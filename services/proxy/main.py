"""Proxy service that receives Discord interactions and publishes to Pub/Sub.
This is a serverless Cloud Run service - Gunicorn handles the server via Procfile.

Discord requires responses within 3 seconds. This service:
- Handles simple commands directly (< 1 second response)
- Uses deferred responses (type 5) for complex commands
- Always responds within 3 seconds to Discord
"""
import traceback
from flask import Flask, request, jsonify

from config import (
    PROJECT_ID,
    PUBSUB_TOPIC_DISCORD_INTERACTIONS
)
from discord_utils import verify_discord_signature, send_discord_response
from interaction_handler import process_interaction, prepare_pubsub_data
from pubsub_utils import get_topic_for_command, publish_to_pubsub
from response_utils import get_error_response

app = Flask(__name__)


@app.route("/health")
def health():
    """Health check endpoint."""
    from config import (
        PUBSUB_TOPIC_DISCORD_INTERACTIONS,
        PUBSUB_TOPIC_DISCORD_COMMANDS_BASE,
        PUBSUB_TOPIC_DISCORD_COMMANDS_ART
    )
    return jsonify({
        'status': 'healthy',
        'service': 'discord-proxy',
        'project_id': PROJECT_ID,
        'topics': {
            'interactions': PUBSUB_TOPIC_DISCORD_INTERACTIONS,
            'commands_base': PUBSUB_TOPIC_DISCORD_COMMANDS_BASE,
            'commands_art': PUBSUB_TOPIC_DISCORD_COMMANDS_ART
        }
    })


@app.route("/discord/response", methods=['POST'])
def receive_processor_response():
    """Receive response from processor and send it to Discord.

    This endpoint is called by processors after they process a command.
    The processor sends the response here, and this service forwards it to Discord.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Missing data'}), 400

        interaction_token = data.get('interaction_token')
        application_id = data.get('application_id')
        response = data.get('response')

        if not interaction_token or not application_id or not response:
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

        success = send_discord_response(interaction_token, application_id, response)
        if success:
            return jsonify({'status': 'sent'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to send to Discord'}), 500

    except Exception as e:
        print(f"ERROR in receive_processor_response: {e}")
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Internal error'}), 500


@app.route("/web/response", methods=['POST'])
def receive_web_response():
    """Receive response from processor for web interactions."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Missing data'}), 400

        token = data.get('token')
        response = data.get('response')

        if not token or not response:
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

        if 'data' in response:
            web_response = {
                'status': 'success',
                'data': response['data']
            }
        else:
            web_response = {
                'status': 'success',
                'data': response
            }

        return jsonify(web_response), 200

    except Exception as e:
        print(f"ERROR in receive_web_response: {e}")
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Internal error'}), 500


@app.route("/web/interactions", methods=['POST'])
def web_interactions():
    """Handle web interactions (non-Discord).

    This endpoint handles interactions from web clients.
    It supports the same commands as Discord but returns JSON responses.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400

        if not data.get('command'):
            return jsonify({'status': 'error', 'message': 'Missing command'}), 400

        result = process_interaction(data, 'web')
        if result:
            response, status_code = result
            return jsonify(response), status_code

        command_name = data.get('command')
        pubsub_data = prepare_pubsub_data(data, 'web')
        topic = get_topic_for_command(command_name)

        try:
            publish_to_pubsub(topic, pubsub_data)
            return jsonify({
                'status': 'processing',
                'message': 'Command is being processed',
                'command': command_name
            }), 202
        except Exception as e:
            print(f"ERROR publishing to Pub/Sub: {e}")
            print(traceback.format_exc())
            response, status_code = get_error_response('web', 'unavailable')
            return jsonify(response), status_code

    except Exception as e:
        print(f"CRITICAL ERROR in web_interactions: {e}")
        print(traceback.format_exc())
        response, status_code = get_error_response('web', 'internal')
        return jsonify(response), status_code


@app.route("/discord/interactions", methods=['POST'])
def discord_interactions():
    """Handle Discord interactions and publish to Pub/Sub."""
    try:
        signature = request.headers.get('X-Signature-Ed25519')
        timestamp = request.headers.get('X-Signature-Timestamp')

        if not signature or not timestamp:
            return 'Bad Request - Missing headers', 400

        if not verify_discord_signature(signature, timestamp, request.get_data()):
            return 'Unauthorized', 401

        interaction = request.get_json()
        if not interaction:
            return 'Bad Request - Invalid JSON', 400

        result = process_interaction(interaction, 'discord')
        if result:
            response, status_code = result
            return jsonify(response), status_code

        if interaction.get('type') == 2:
            command_name = interaction.get('data', {}).get('name')
            topic = get_topic_for_command(command_name)
        else:
            topic = PUBSUB_TOPIC_DISCORD_INTERACTIONS

        pubsub_data = prepare_pubsub_data(interaction, 'discord', signature, timestamp)

        try:
            publish_to_pubsub(topic, pubsub_data)
            return jsonify({'type': 5})
        except Exception as e:
            print(f"ERROR publishing to Pub/Sub: {e}")
            print(traceback.format_exc())
            response, status_code = get_error_response('discord', 'unavailable')
            return jsonify(response), status_code

    except Exception as e:
        print(f"CRITICAL ERROR in discord_interactions: {e}")
        print(traceback.format_exc())
        response, status_code = get_error_response('discord', 'internal')
        return jsonify(response), status_code
