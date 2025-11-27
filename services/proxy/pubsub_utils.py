"""Pub/Sub utilities."""
import json
from typing import Optional
from google.cloud import pubsub_v1

from config import PROJECT_ID, PUBSUB_TOPIC_COMMANDS_BASE

publisher = pubsub_v1.PublisherClient()

def get_topic_for_command(command_name: str) -> str:
    """Get Pub/Sub topic for a command.

    Routes commands to specialized microservices:
    - draw -> commands-draw
    - snapshot -> commands-snapshot
    - canvas_state -> commands-canvas-state
    - stats -> commands-stats
    - colors -> commands-colors
    - pixel_info, getpixel -> commands-pixel-info
    - Others -> commands-base
    """
    # Microservices routing
    command_topic_map = {
        'draw': 'commands-draw',
        'snapshot': 'commands-snapshot',
        'canvas_state': 'commands-canvas-state',
        'stats': 'commands-stats',
        'colors': 'commands-colors',
        'pixel_info': 'commands-pixel-info',
        'getpixel': 'commands-pixel-info',
    }

    # Check if command has dedicated topic
    if command_name in command_topic_map:
        return command_topic_map[command_name]

    # Fallback to base topic for unknown commands
    return PUBSUB_TOPIC_COMMANDS_BASE


def publish_to_pubsub(topic_name: str, data: dict, logger=None, correlation_id: Optional[str] = None) -> str:
    """Publish message to Pub/Sub topic.

    Args:
        topic_name: Name of the Pub/Sub topic
        data: Dictionary data to publish
        logger: Logger instance (optional)
        correlation_id: Correlation ID for tracing (optional)

    Returns:
        Message ID from Pub/Sub

    Raises:
        ValueError: If PROJECT_ID is not configured
        Exception: If publishing fails
    """
    try:
        if not PROJECT_ID:
            raise ValueError("PROJECT_ID not configured")

        topic_path = publisher.topic_path(PROJECT_ID, topic_name)

        # --- Extract command name for logging ---
        command_name = None
        interaction = data.get('interaction', {})
        if interaction:
            command_name = interaction.get('data', {}).get('name')

        if logger:
            logger.info(
                "Publishing message to Pub/Sub",
                correlation_id=correlation_id,
                topic=topic_name,
                command_name=command_name,
                interaction_type=data.get('interaction_type', 'discord')
            )

        message_data = json.dumps(data).encode('utf-8')
        message_size = len(message_data)

        future = publisher.publish(topic_path, message_data)
        message_id = future.result(timeout=10)

        if logger:
            logger.info(
                "Message published to Pub/Sub successfully",
                correlation_id=correlation_id,
                topic=topic_name,
                message_id=message_id,
                message_size_bytes=message_size,
                command_name=command_name
            )

        return message_id
    except ValueError as e:
        if logger:
            logger.error(
                "Configuration error publishing to Pub/Sub",
                correlation_id=correlation_id,
                topic=topic_name,
                error=str(e)
            )
        raise
    except Exception as e:
        if logger:
            logger.error(
                "Failed to publish message to Pub/Sub",
                correlation_id=correlation_id,
                topic=topic_name,
                command_name=command_name,
                error=e
            )
        raise

