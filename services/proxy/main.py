"""Proxy service that receives Discord interactions and publishes to Pub/Sub.
Uses Functions Framework for Cloud Run

Discord requires responses within 3 seconds. This service:
- Handles simple commands directly (< 1 second response)
- Uses deferred responses (type 5) for complex commands
- Always responds within 3 seconds to Discord
"""
import sys
import os
import traceback

# Import shared modules (copied to service directory during deployment)
from shared.observability import init_observability, traced_function
from shared.flask_middleware import add_correlation_middleware
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

# Initialize observability
logger, tracing = init_observability('discord-proxy', app=app)
add_correlation_middleware(app, logger)


@app.route("/health", methods=['GET'])
def health(request):
    """Health check endpoint."""
    logger.info("Health check called", correlation_id=getattr(g, 'correlation_id', None))
    
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
@traced_function("send_discord_response")
def receive_processor_response(request):
    """Receive response from processor and send it to Discord.

    This endpoint is called by processors after they process a command.
    The processor sends the response here, and this service forwards it to Discord.
    """
    correlation_id = getattr(g, 'correlation_id', None)
    
    try:
        data = request.get_json(silent=True)
        if not data:
            logger.warning("Missing data in response", correlation_id=correlation_id)
            return {'status': 'error', 'message': 'Missing data'}, 400

        interaction_token = data.get('interaction_token')
        application_id = data.get('application_id')
        response = data.get('response')

        if not interaction_token or not application_id or not response:
            logger.warning(
                "Missing required fields",
                correlation_id=correlation_id,
                has_token=bool(interaction_token),
                has_app_id=bool(application_id),
                has_response=bool(response)
            )
            return {'status': 'error', 'message': 'Missing required fields'}, 400

        logger.info(
            "Sending response to Discord",
            correlation_id=correlation_id,
            interaction_token=interaction_token[:10] + "..." if interaction_token else None
        )
        
        success = send_discord_response(interaction_token, application_id, response)
        if success:
            logger.info("Response sent successfully to Discord", correlation_id=correlation_id)
            return {'status': 'sent'}, 200
        else:
            logger.error("Failed to send to Discord", correlation_id=correlation_id)
            return {'status': 'error', 'message': 'Failed to send to Discord'}, 500

    except Exception as e:
        logger.error("Error in receive_processor_response", error=e, correlation_id=correlation_id)
        return {'status': 'error', 'message': 'Internal error'}, 500


@app.route("/web/response", methods=['POST'])
def receive_web_response(request):
    """Receive response from processor for web interactions."""
    correlation_id = getattr(g, 'correlation_id', None)
    
    try:
        data = request.get_json(silent=True)
        if not data:
            logger.warning("Missing data in web response", correlation_id=correlation_id)
            return {'status': 'error', 'message': 'Missing data'}, 400

        token = data.get('token')
        response = data.get('response')

        if not token or not response:
            logger.warning("Missing required fields in web response", correlation_id=correlation_id)
            return {'status': 'error', 'message': 'Missing required fields'}, 400

        logger.info("Processing web response", correlation_id=correlation_id, token=token[:10] + "..." if token else None)

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
        logger.error("Error in receive_web_response", error=e, correlation_id=correlation_id)
        return {'status': 'error', 'message': 'Internal error'}, 500



@app.route("/web/interactions", methods=['POST'])
def web_interactions(request):
    """Handle web interactions (non-Discord).

    This endpoint handles interactions from web clients.
    It supports the same commands as Discord but returns JSON responses.
    """
    correlation_id = getattr(g, 'correlation_id', None)
    
    try:
        data = request.get_json(silent=True)
        if not data:
            logger.warning("Invalid JSON in web interaction", correlation_id=correlation_id)
            return {'status': 'error', 'message': 'Invalid JSON'}, 400

        if not data.get('command'):
            logger.warning("Missing command in web interaction", correlation_id=correlation_id)
            return {'status': 'error', 'message': 'Invalid JSON'}, 400

        if not data.get('command'):
            return {'status': 'error', 'message': 'Missing command'}, 400

        command_name = data.get('command')
        logger.info("Processing web interaction", correlation_id=correlation_id, command=command_name)

        result = process_interaction(data, 'web')
        if result:
            response, status_code = result
            logger.info("Web interaction processed immediately", correlation_id=correlation_id, status_code=status_code)
            return response, status_code

        pubsub_data = prepare_pubsub_data(data, 'web')
        pubsub_data['correlation_id'] = correlation_id  # Propagate correlation ID
            return response, status_code

        command_name = data.get('command')
        pubsub_data = prepare_pubsub_data(data, 'web', request=request)
        topic = get_topic_for_command(command_name)

        try:
            publish_to_pubsub(topic, pubsub_data)
            logger.info("Published web interaction to Pub/Sub", correlation_id=correlation_id, topic=topic, command=command_name)
            return {
                'status': 'processing',
                'message': 'Command is being processed',
                'command': command_name
            }, 202
        except Exception as e:
            logger.error("Failed to publish web interaction to Pub/Sub", error=e, correlation_id=correlation_id, topic=topic)
            response, status_code = get_error_response('web', 'unavailable')
            return response, status_code

    except Exception as e:
        logger.error("Critical error in web_interactions", error=e, correlation_id=correlation_id)
        response, status_code = get_error_response('web', 'internal')
        return response, status_code


@app.route("/discord/interactions", methods=['POST'])
@traced_function("discord_interaction")
def discord_interactions(request):
    """Handle Discord interactions and publish to Pub/Sub."""
    correlation_id = getattr(g, 'correlation_id', None)
    
    try:
        signature = request.headers.get('X-Signature-Ed25519')
        timestamp = request.headers.get('X-Signature-Timestamp')

        if not signature or not timestamp:
            logger.warning("Missing Discord signature headers", correlation_id=correlation_id)
            return 'Bad Request - Missing headers', 400

        if not verify_discord_signature(signature, timestamp, request.get_data()):
            logger.warning("Invalid Discord signature", correlation_id=correlation_id)
        body = request.get_data()
        if not verify_discord_signature(signature, timestamp, body):
            return 'Unauthorized', 401

        interaction = request.get_json(silent=True)
        if not interaction:
            logger.warning("Invalid JSON in Discord interaction", correlation_id=correlation_id)
            return 'Bad Request - Invalid JSON', 400

        interaction_type = interaction.get('type')
        interaction_id = interaction.get('id')
        
        logger.info(
            "Processing Discord interaction",
            correlation_id=correlation_id,
            interaction_type=interaction_type,
            interaction_id=interaction_id
        )

        result = process_interaction(interaction, 'discord')
        if result:
            response, status_code = result
            logger.info(
                "Discord interaction processed immediately",
                correlation_id=correlation_id,
                status_code=status_code
            )
            return response, status_code

        if interaction.get('type') == 2:
            command_name = interaction.get('data', {}).get('name')
            topic = get_topic_for_command(command_name)
            logger.info(
                "Discord command received",
                correlation_id=correlation_id,
                command_name=command_name,
                topic=topic
            )
        else:
            topic = PUBSUB_TOPIC_DISCORD_INTERACTIONS

        pubsub_data = prepare_pubsub_data(interaction, 'discord', signature, timestamp)
        pubsub_data['correlation_id'] = correlation_id  # Propagate correlation ID

        try:
            publish_to_pubsub(topic, pubsub_data)
            logger.info(
                "Published Discord interaction to Pub/Sub",
                correlation_id=correlation_id,
                topic=topic
            )
            return {'type': 5}, 200
        except Exception as e:
            logger.error(
                "Failed to publish Discord interaction to Pub/Sub",
                error=e,
                correlation_id=correlation_id,
                topic=topic
            )
            response, status_code = get_error_response('discord', 'unavailable')
            return response, status_code

    except Exception as e:
        logger.error(
            "Critical error in discord_interactions",
            error=e,
            correlation_id=correlation_id
        )
        response, status_code = get_error_response('discord', 'internal')
        return response, status_code
