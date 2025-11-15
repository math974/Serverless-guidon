"""Proxy service that receives Discord interactions and publishes to Pub/Sub.
Uses Functions Framework for Cloud Run

Discord requires responses within 3 seconds. This service:
- Handles simple commands directly (< 1 second response)
- Uses deferred responses (type 5) for complex commands
- Always responds within 3 seconds to Discord
"""
import traceback
from functions_framework import create_app

from config import (
    PROJECT_ID,
    PUBSUB_TOPIC_DISCORD_INTERACTIONS
)
from discord_utils import verify_discord_signature, send_discord_response
from interaction_handler import process_interaction, prepare_pubsub_data
from pubsub_utils import get_topic_for_command, publish_to_pubsub
from response_utils import get_error_response

app = create_app(__name__)

@app.route("/health", methods=['GET'])
def health(request):
    """Health check endpoint."""
    from config import (
        PUBSUB_TOPIC_DISCORD_INTERACTIONS,
        PUBSUB_TOPIC_DISCORD_COMMANDS_BASE,
        PUBSUB_TOPIC_DISCORD_COMMANDS_ART
    )
    return {
        'status': 'healthy',
        'service': 'discord-proxy',
        'project_id': PROJECT_ID,
        'topics': {
            'interactions': PUBSUB_TOPIC_DISCORD_INTERACTIONS,
            'commands_base': PUBSUB_TOPIC_DISCORD_COMMANDS_BASE,
            'commands_art': PUBSUB_TOPIC_DISCORD_COMMANDS_ART
        }
    }, 200


@app.route("/discord/response", methods=['POST'])
def receive_processor_response(request):
    """Receive response from processor and send it to Discord.

    This endpoint is called by processors after they process a command.
    The processor sends the response here, and this service forwards it to Discord.
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return {'status': 'error', 'message': 'Missing data'}, 400

        interaction_token = data.get('interaction_token')
        application_id = data.get('application_id')
        response = data.get('response')

        if not interaction_token or not application_id or not response:
            return {'status': 'error', 'message': 'Missing required fields'}, 400

        success = send_discord_response(interaction_token, application_id, response)
        if success:
            return {'status': 'sent'}, 200
        else:
            return {'status': 'error', 'message': 'Failed to send to Discord'}, 500

    except Exception as e:
        print(f"ERROR in receive_processor_response: {e}")
        print(traceback.format_exc())
        return {'status': 'error', 'message': 'Internal error'}, 500


@app.route("/web/response", methods=['POST'])
def receive_web_response(request):
    """Receive response from processor for web interactions."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return {'status': 'error', 'message': 'Missing data'}, 400

        token = data.get('token')
        response = data.get('response')

        if not token or not response:
            return {'status': 'error', 'message': 'Missing required fields'}, 400

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

        return web_response, 200

    except Exception as e:
        print(f"ERROR in receive_web_response: {e}")
        print(traceback.format_exc())
        return {'status': 'error', 'message': 'Internal error'}, 500

@app.route("/web/interactions", methods=['POST'])
def web_interactions(request):
    """Handle web interactions (non-Discord).

    This endpoint handles interactions from web clients.
    It supports the same commands as Discord but returns JSON responses.
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return {'status': 'error', 'message': 'Invalid JSON'}, 400

        if not data.get('command'):
            return {'status': 'error', 'message': 'Missing command'}, 400

        result = process_interaction(data, 'web')
        if result:
            response, status_code = result
            return response, status_code

        command_name = data.get('command')
        pubsub_data = prepare_pubsub_data(data, 'web', request=request)
        topic = get_topic_for_command(command_name)

        try:
            publish_to_pubsub(topic, pubsub_data)
            return {
                'status': 'processing',
                'message': 'Command is being processed',
                'command': command_name
            }, 202
        except Exception as e:
            print(f"ERROR publishing to Pub/Sub: {e}")
            print(traceback.format_exc())
            response, status_code = get_error_response('web', 'unavailable')
            return response, status_code

    except Exception as e:
        print(f"CRITICAL ERROR in web_interactions: {e}")
        print(traceback.format_exc())
        response, status_code = get_error_response('web', 'internal')
        return response, status_code


@app.route("/discord/interactions", methods=['POST'])
def discord_interactions(request):
    """Handle Discord interactions and publish to Pub/Sub."""
    try:
        signature = request.headers.get('X-Signature-Ed25519')
        timestamp = request.headers.get('X-Signature-Timestamp')

        if not signature or not timestamp:
            return 'Bad Request - Missing headers', 400

        body = request.get_data()
        if not verify_discord_signature(signature, timestamp, body):
            return 'Unauthorized', 401

        interaction = request.get_json(silent=True)
        if not interaction:
            return 'Bad Request - Invalid JSON', 400

        result = process_interaction(interaction, 'discord')
        if result:
            response, status_code = result
            return response, status_code

        if interaction.get('type') == 2:
            command_name = interaction.get('data', {}).get('name')
            topic = get_topic_for_command(command_name)
        else:
            topic = PUBSUB_TOPIC_DISCORD_INTERACTIONS

        pubsub_data = prepare_pubsub_data(interaction, 'discord', signature, timestamp, request)

        try:
            publish_to_pubsub(topic, pubsub_data)
            return {'type': 5}, 200
        except Exception as e:
            print(f"ERROR publishing to Pub/Sub: {e}")
            print(traceback.format_exc())
            response, status_code = get_error_response('discord', 'unavailable')
            return response, status_code

    except Exception as e:
        print(f"CRITICAL ERROR in discord_interactions: {e}")
        print(traceback.format_exc())
        response, status_code = get_error_response('discord', 'internal')
        return response, status_code
