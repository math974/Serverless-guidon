"""Shared Pub/Sub message processing utilities."""
import json
import base64
import os
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
    """Handle sending response directly to Discord or web webhooks.

    Args:
        interaction_data: Decoded Pub/Sub message data
        response: Processed response dict
        logger: Logger instance (optional)

    Returns:
        True if response was sent successfully, False otherwise
    """
    from shared.processor_utils import send_discord_webhook_direct, send_web_webhook

    interaction = interaction_data.get('interaction', {})
    interaction_type = interaction_data.get('interaction_type', 'discord')
    correlation_id = interaction_data.get('correlation_id')

    if logger:
        logger.info(
            "handle_processor_response called",
            correlation_id=correlation_id,
            interaction_type=interaction_type,
            has_response=bool(response),
            has_webhook_url=bool(interaction_data.get('webhook_url'))
        )

    # For web interactions, use webhook_url directly
    if interaction_type == 'web':
        webhook_url = interaction_data.get('webhook_url')
        if not webhook_url:
            if logger:
                logger.warning("Web interaction but no webhook_url provided", correlation_id=correlation_id)
            return False

        if logger:
            logger.info(
                "Sending web webhook response",
                correlation_id=correlation_id,
                webhook_url=webhook_url
            )

        token = (
            response.get('token')
            or interaction.get('token')
            or interaction_data.get('token')
        )
        if not token and logger:
            logger.warning("Web interaction missing token in payload", correlation_id=correlation_id)

        response_payload = dict(response)
        if token:
            response_payload['token'] = token

        return send_web_webhook(webhook_url, response_payload, correlation_id, logger)

    # For Discord interactions, send directly to Discord webhook
    interaction_token = interaction.get('token')
    application_id = interaction.get('application_id')
    discord_bot_token = interaction_data.get('discord_bot_token') or os.environ.get('DISCORD_BOT_TOKEN')

    if interaction_token and application_id and discord_bot_token:
        return send_discord_webhook_direct(
            interaction_token, application_id, response, discord_bot_token, correlation_id, logger
        )
    else:
        if logger:
            logger.warning(
                "Missing required Discord webhook parameters",
                correlation_id=correlation_id,
                has_token=bool(interaction_token),
                has_app_id=bool(application_id),
                has_bot_token=bool(discord_bot_token)
            )
        return False
