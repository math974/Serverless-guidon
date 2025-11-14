"""Cloud Run service that processes Pub/Sub messages for art Discord commands.
This is a serverless Cloud Run service - Gunicorn handles the server via Procfile.
"""
import os
import json
import base64
from flask import Flask, request, jsonify
import requests

from command_registry import CommandHandler
import handlers

app = Flask(__name__)


def send_response_to_proxy(proxy_url: str, interaction_token: str, application_id: str, response: dict):
    """Send response to proxy service, which will forward it to Discord."""
    if not proxy_url:
        print("Proxy URL not provided, cannot send response")
        return False

    url = f"{proxy_url}/discord/response"
    payload = {
        'interaction_token': interaction_token,
        'application_id': application_id,
        'response': response
    }

    try:
        result = requests.post(url, json=payload, timeout=10)
        if result.status_code == 200:
            print(f"Response sent to proxy for interaction {interaction_token}")
            return True
        else:
            print(f"Error sending response to proxy: {result.status_code} - {result.text}")
            return False
    except Exception as e:
        print(f"Error sending response to proxy: {e}")
        return False


def process_discord_interaction(interaction: dict) -> dict:
    """Process a Discord interaction and return response."""
    try:
        interaction_type = interaction.get('type')

        if interaction_type == 1:
            return {'type': 1}

        if interaction_type == 2:
            command_name = interaction.get('data', {}).get('name')
            if not command_name:
                raise ValueError("Missing command name in interaction data")
            return CommandHandler.handle(command_name, interaction)

        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Unknown Interaction Type',
                    'description': 'This interaction type is not supported.',
                    'color': 0xFF0000
                }]
            }
        }
    except Exception as e:
        import traceback
        print(f"ERROR processing interaction: {e}")
        print(traceback.format_exc())

        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Processing Error',
                    'description': 'An unexpected error occurred. The service is still running.',
                    'color': 0xFF0000,
                    'footer': {
                        'text': 'Error logged - service continues running'
                    }
                }]
            }
        }


@app.route("/", methods=['POST'])
def process_pubsub_message():
    """Process Pub/Sub push message."""
    try:
        envelope = request.get_json()

        if not envelope:
            return jsonify({'status': 'error', 'message': 'Missing envelope'}), 400

        pubsub_message = envelope.get('message', {})
        if not pubsub_message:
            return jsonify({'status': 'error', 'message': 'Missing message'}), 400

        try:
            message_data = base64.b64decode(pubsub_message.get('data', '')).decode('utf-8')
            interaction_data = json.loads(message_data)
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            print(f"ERROR decoding Pub/Sub message: {e}")
            return jsonify({'status': 'error', 'message': 'Invalid message format'}), 400

        interaction = interaction_data.get('interaction', {})
        if not interaction:
            return jsonify({'status': 'error', 'message': 'Missing interaction'}), 400

        proxy_url = interaction_data.get('proxy_url')
        interaction_type = interaction_data.get('interaction_type', 'discord')
        response = process_discord_interaction(interaction)

        interaction_token = interaction.get('token')
        application_id = interaction.get('application_id')

        if interaction_type == 'web' and proxy_url:
            try:
                web_response_url = f"{proxy_url}/web/response"
                web_payload = {
                    'token': interaction_token,
                    'response': response
                }
                requests.post(web_response_url, json=web_payload, timeout=10)
            except Exception as e:
                print(f"ERROR sending web response: {e}")
        elif interaction_token and application_id and proxy_url:
            try:
                send_response_to_proxy(proxy_url, interaction_token, application_id, response)
            except Exception as e:
                print(f"ERROR sending response to proxy: {e}")
                import traceback
                traceback.print_exc()

        return jsonify({'status': 'processed'}), 200

    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR in process_pubsub_message: {e}")
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Internal error (logged)'}), 200


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'discord-processor-art',
        'handlers': list(CommandHandler.HANDLERS.keys())
    })

