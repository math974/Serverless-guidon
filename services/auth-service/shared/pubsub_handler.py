"""Shared Pub/Sub message processing utilities."""
import json
import base64
from typing import Optional, Dict, Tuple

def decode_pubsub_message(request, logger=None) -> Tuple[Optional[Dict], Optional[str]]:
    """Decode Pub/Sub push message from request.

    Args:
        request: Functions Framework request object
        logger: Logger instance (optional)

    Returns:
        Tuple of (interaction_data, correlation_id) or (None, None) on error
    """
    try:
        envelope = request.get_json(silent=True)

        if not envelope:
            if logger:
                logger.warning("Missing envelope in Pub/Sub message")
            return None, None

        pubsub_message = envelope.get('message', {})
        if not pubsub_message:
            if logger:
                logger.warning("Missing message in Pub/Sub envelope")
            return None, None

        try:
            message_data = base64.b64decode(pubsub_message.get('data', '')).decode('utf-8')
            interaction_data = json.loads(message_data)
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            if logger:
                logger.error("Error decoding Pub/Sub message", error=e)
            return None, None

        correlation_id = interaction_data.get('correlation_id', 'unknown')
        return interaction_data, correlation_id

    except Exception as e:
        if logger:
            logger.error("Error processing Pub/Sub envelope", error=e)
        return None, None


def handle_processor_response(
    interaction_data: dict,
    response: dict,
    logger=None
) -> bool:
    """Handle sending response back to proxy (Discord or web).

    Args:
        interaction_data: Decoded Pub/Sub message data
        response: Processed response dict
        logger: Logger instance (optional)

    Returns:
        True if response was sent successfully, False otherwise
    """
    from shared.processor_utils import send_response_to_proxy, send_web_response

    interaction = interaction_data.get('interaction', {})
    proxy_url = interaction_data.get('proxy_url')
    interaction_type = interaction_data.get('interaction_type', 'discord')
    correlation_id = interaction_data.get('correlation_id')

    interaction_token = interaction.get('token')
    application_id = interaction.get('application_id')

    if interaction_type == 'web' and proxy_url:
        return send_web_response(proxy_url, interaction_token, response, correlation_id, logger)
    elif interaction_token and application_id and proxy_url:
        return send_response_to_proxy(
            proxy_url, interaction_token, application_id, response, correlation_id, logger
        )

    return False
