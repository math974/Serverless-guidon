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
    PUBSUB_TOPIC_INTERACTIONS
)
from discord_utils import verify_discord_signature
from interaction_handler import process_interaction, prepare_pubsub_data
from pubsub_utils import get_topic_for_command, publish_to_pubsub
from response_utils import get_error_response
from shared.correlation import with_correlation

logger, tracing = init_observability('discord-proxy', app=None)


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

    # --- Web interactions endpoint ---
    if path == "/web/interactions" and method == "POST":
        result = web_interactions(request)
        response = result if isinstance(result, Response) else make_response(result[0], result[1]) if isinstance(result, tuple) else result
        return add_cors_headers(response)

    # --- Discord interactions endpoint ---
    if path == "/discord/interactions" and method == "POST":
        return discord_interactions(request)

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
        PUBSUB_TOPIC_INTERACTIONS,
        PUBSUB_TOPIC_COMMANDS_BASE
    )
    return jsonify({
        'status': 'healthy',
        'service': 'discord-proxy',
        'project_id': PROJECT_ID,
        'topics': {
            'interactions': PUBSUB_TOPIC_INTERACTIONS,
            'commands_base': PUBSUB_TOPIC_COMMANDS_BASE
        }
    }), 200


@traced_function("web_interactions")
def web_interactions(request: Request):
    """Handle web interactions."""
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
                'command': command_name
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
            topic = PUBSUB_TOPIC_INTERACTIONS

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
