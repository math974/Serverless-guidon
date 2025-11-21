"""Proxy service that receives Discord interactions and publishes to Pub/Sub.
Uses Functions Framework for Cloud Functions Gen2

Discord requires responses within 3 seconds. This service:
- Handles simple commands directly (< 1 second response)
- Uses deferred responses (type 5) for complex commands
- Always responds within 3 seconds to Discord
"""
from functions_framework import http
from flask import Request, jsonify, make_response, Response

from shared.observability import init_observability, traced_function
from config import (
    PROJECT_ID,
    PUBSUB_TOPIC_DISCORD_INTERACTIONS
)
from discord_utils import verify_discord_signature, send_discord_response
from interaction_handler import process_interaction, prepare_pubsub_data
from pubsub_utils import get_topic_for_command, publish_to_pubsub
from response_utils import get_error_response
from shared.correlation import with_correlation

logger, tracing = init_observability('discord-proxy', app=None)

# In-memory storage for web responses (token -> response)
# In production, consider using Firestore or Redis for persistence
_web_responses = {}


def add_cors_headers(response):
    """Add CORS headers to response."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Session-ID, X-Correlation-ID, Authorization'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response


@http
@with_correlation(logger)
@traced_function("proxy_handler")
def proxy_handler(request: Request):
    """Main HTTP handler for proxy service.

    Routes requests to appropriate handlers based on path.
    """
    path = request.path
    method = request.method

    # Handle CORS preflight requests
    if method == 'OPTIONS':
        response = make_response('', 200)
        return add_cors_headers(response)

    # --- Health check ---
    if path == "/health" and method == "GET":
        response = health_handler(request)
        return add_cors_headers(response)

    # --- Discord response endpoint ---
    if path == "/discord/response" and method == "POST":
        return receive_processor_response(request)

    # --- Web response endpoint ---
    if path == "/web/response" and method == "POST":
        result = receive_web_response(request)
        response = result if isinstance(result, Response) else make_response(result[0], result[1]) if isinstance(result, tuple) else result
        return add_cors_headers(response)

    # --- Get web response by token ---
    if path.startswith("/web/response/") and method == "GET":
        token = path.split("/web/response/")[-1]
        result = get_web_response(token)
        response = result if isinstance(result, Response) else make_response(result[0], result[1]) if isinstance(result, tuple) else result
        return add_cors_headers(response)

    # --- Web interactions endpoint ---
    if path == "/web/interactions" and method == "POST":
        result = web_interactions(request)
        response = result if isinstance(result, Response) else make_response(result[0], result[1]) if isinstance(result, tuple) else result
        return add_cors_headers(response)

    # --- Discord interactions endpoint ---
    if path == "/discord/interactions" and method == "POST":
        return discord_interactions(request)

    # 404 for unknown paths
    logger.warning("Unknown path", path=path, method=method)
    response = jsonify({'error': 'Not found'}), 404
    if isinstance(response, tuple):
        response = make_response(response[0], response[1])
    return add_cors_headers(response)

def health_handler(request: Request):
    """Health check endpoint."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))
    logger.info("Health check called", correlation_id=correlation_id)

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
    }), 200


@traced_function("send_discord_response")
def receive_processor_response(request: Request):
    """Receive response from processor and send it to Discord.

    This endpoint is called by processors after they process a command.
    The processor sends the response here, and this service forwards it to Discord.
    """
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    try:
        data = request.get_json(silent=True)
        if not data:
            logger.warning("Missing data in response", correlation_id=correlation_id)
            return jsonify({'status': 'error', 'message': 'Missing data'}), 400

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
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

        logger.info(
            "Sending response to Discord",
            correlation_id=correlation_id,
            interaction_token=interaction_token[:10] + "..." if interaction_token else None
        )

        success = send_discord_response(interaction_token, application_id, response)
        if success:
            logger.info("Response sent successfully to Discord", correlation_id=correlation_id)
            return jsonify({'status': 'sent'}), 200
        else:
            logger.error("Failed to send to Discord", correlation_id=correlation_id)
            return jsonify({'status': 'error', 'message': 'Failed to send to Discord'}), 500

    except Exception as e:
        logger.error("Error in receive_processor_response", error=e, correlation_id=correlation_id)
        return jsonify({'status': 'error', 'message': 'Internal error'}), 500


def receive_web_response(request: Request):
    """Receive response from processor for web interactions and store it."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    try:
        data = request.get_json(silent=True)
        if not data:
            logger.warning("Missing data in web response", correlation_id=correlation_id)
            return jsonify({'status': 'error', 'message': 'Missing data'}), 400

        token = data.get('token')
        response = data.get('response')

        if not token or not response:
            logger.warning("Missing required fields in web response", correlation_id=correlation_id)
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

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

        # Store response for retrieval by token
        _web_responses[token] = web_response
        logger.info("Stored web response", correlation_id=correlation_id, token=token[:10] + "...")

        return jsonify(web_response), 200

    except Exception as e:
        logger.error("Error in receive_web_response", error=e, correlation_id=correlation_id)
        return jsonify({'status': 'error', 'message': 'Internal error'}), 500


def get_web_response(token: str):
    """Get stored web response by token."""
    if not token:
        response = jsonify({'status': 'error', 'message': 'Missing token'})
        return add_cors_headers(response), 400

    logger.info("Getting web response", token=token[:10] + "...")

    if token in _web_responses:
        response = _web_responses[token]
        # Delete after retrieval to save memory
        del _web_responses[token]
        result = jsonify(response)
        return add_cors_headers(result), 200
    else:
        result = jsonify({'status': 'processing', 'message': 'Response not ready yet'})
        return add_cors_headers(result), 202


def web_interactions(request: Request):
    """Handle web interactions (non-Discord).

    This endpoint handles interactions from web clients.
    It supports the same commands as Discord but returns JSON responses.
    """
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    try:
        data = request.get_json(silent=True)
        if not data:
            logger.warning("Invalid JSON in web interaction", correlation_id=correlation_id)
            return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400

        command_name = data.get('command')
        if not command_name:
            logger.warning("Missing command in web interaction", correlation_id=correlation_id)
            return jsonify({'status': 'error', 'message': 'Missing command'}), 400

        logger.info("Processing web interaction", correlation_id=correlation_id, command=command_name)

        result = process_interaction(data, 'web', correlation_id=correlation_id)
        if result:
            response, status_code = result
            logger.info("Web interaction processed immediately", correlation_id=correlation_id, status_code=status_code)
            return jsonify(response), status_code

        pubsub_data = prepare_pubsub_data(data, 'web', request=request)
        pubsub_data['correlation_id'] = correlation_id  # Propagate correlation ID
        topic = get_topic_for_command(command_name)

        # Get token from interaction data for polling
        token = data.get('token') or pubsub_data.get('interaction', {}).get('token')

        try:
            message_id = publish_to_pubsub(topic, pubsub_data, logger=logger, correlation_id=correlation_id)
            logger.info(
                "Published web interaction to Pub/Sub",
                correlation_id=correlation_id,
                topic=topic,
                command=command_name,
                message_id=message_id
            )
            return jsonify({
                'status': 'processing',
                'message': 'Command is being processed',
                'command': command_name,
                'token': token
            }), 202
        except Exception as e:
            logger.error("Failed to publish web interaction to Pub/Sub", error=e, correlation_id=correlation_id, topic=topic)
            response, status_code = get_error_response('web', 'unavailable')
            return jsonify(response), status_code

    except Exception as e:
        logger.error("Critical error in web_interactions", error=e, correlation_id=correlation_id)
        response, status_code = get_error_response('web', 'internal')
        return jsonify(response), status_code


@traced_function("discord_interaction")
def discord_interactions(request: Request):
    """Handle Discord interactions and publish to Pub/Sub."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    try:
        signature = request.headers.get('X-Signature-Ed25519')
        timestamp = request.headers.get('X-Signature-Timestamp')

        if not signature or not timestamp:
            logger.warning("Missing Discord signature headers", correlation_id=correlation_id)
            return jsonify({'error': 'Bad Request - Missing headers'}), 400

        body = request.get_data()
        if not verify_discord_signature(signature, timestamp, body):
            logger.warning("Invalid Discord signature", correlation_id=correlation_id)
            return jsonify({'error': 'Unauthorized'}), 401

        interaction = request.get_json(silent=True)
        if not interaction:
            logger.warning("Invalid JSON in Discord interaction", correlation_id=correlation_id)
            return jsonify({'error': 'Bad Request - Invalid JSON'}), 400

        interaction_type = interaction.get('type')
        interaction_id = interaction.get('id')

        logger.info(
            "Processing Discord interaction",
            correlation_id=correlation_id,
            interaction_type=interaction_type,
            interaction_id=interaction_id
        )

        result = process_interaction(interaction, 'discord', correlation_id=correlation_id)
        if result:
            response, status_code = result
            logger.info(
                "Discord interaction processed immediately",
                correlation_id=correlation_id,
                status_code=status_code
            )
            return jsonify(response), status_code

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

        pubsub_data = prepare_pubsub_data(interaction, 'discord', signature, timestamp, request)
        pubsub_data['correlation_id'] = correlation_id  # Propagate correlation ID

        try:
            message_id = publish_to_pubsub(topic, pubsub_data, logger=logger, correlation_id=correlation_id)
            logger.info(
                "Published Discord interaction to Pub/Sub",
                correlation_id=correlation_id,
                topic=topic,
                message_id=message_id,
                command_name=command_name if interaction.get('type') == 2 else None
            )
            return jsonify({'type': 5}), 200
        except Exception as e:
            logger.error(
                "Failed to publish Discord interaction to Pub/Sub",
                error=e,
                correlation_id=correlation_id,
                topic=topic
            )
            response, status_code = get_error_response('discord', 'unavailable')
            return jsonify(response), status_code

    except Exception as e:
        logger.error(
            "Critical error in discord_interactions",
            error=e,
            correlation_id=correlation_id
        )
        response, status_code = get_error_response('discord', 'internal')
        return jsonify(response), status_code
