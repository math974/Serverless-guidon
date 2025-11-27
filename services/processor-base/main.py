"""Cloud Functions service that processes Pub/Sub messages for base Discord commands.
Uses Functions Framework for Cloud Functions Gen2
"""
import json
import base64
from functions_framework import cloud_event
from cloudevents.http import CloudEvent

from shared.observability import init_observability, traced_function
from shared.processor_utils import process_interaction
from shared.pubsub_handler import handle_processor_response
from command_registry import CommandHandler

# Import handlers to register them
import handlers  # noqa: F401

logger, tracing = init_observability('discord-processor-base', app=None)


@cloud_event
@traced_function("processor_base_handler")
def processor_base_handler(cloud_event: CloudEvent):
    """Process Pub/Sub message from CloudEvent.

    Args:
        cloud_event: CloudEvent containing Pub/Sub message data
    """
    correlation_id = None

    try:
        # --- Extract Pub/Sub message from CloudEvent ---
        message_data = cloud_event.data
        event_id = getattr(cloud_event, 'id', None)

        if not message_data:
            logger.warning("Missing data in CloudEvent", event_id=event_id)
            return

        # --- Log CloudEvent metadata ---
        event_source = getattr(cloud_event, 'source', None)
        event_type = getattr(cloud_event, 'type', None)

        logger.info(
            "Received CloudEvent from Pub/Sub",
            event_id=event_id,
            event_source=event_source,
            event_type=event_type
        )

        # --- Decode base64 message data ---
        try:
            if isinstance(message_data.get('message', {}).get('data'), str):
                encoded_data = message_data['message']['data']
                decoded_data = base64.b64decode(encoded_data).decode('utf-8')
                interaction_data = json.loads(decoded_data)
                logger.debug(
                    "Decoded base64 Pub/Sub message",
                    message_size_bytes=len(encoded_data)
                )
            else:
                # --- If data is already decoded ---
                interaction_data = message_data
                logger.debug("Using already decoded Pub/Sub message")
        except (ValueError, TypeError, json.JSONDecodeError, KeyError) as e:
            logger.error(
                "Error decoding Pub/Sub message",
                error=e,
                event_id=event_id,
                has_message=bool(message_data.get('message'))
            )
            return

        correlation_id = interaction_data.get('correlation_id', 'unknown')
        interaction = interaction_data.get('interaction', {})

        if not interaction:
            logger.warning(
                "Missing interaction in message",
                correlation_id=correlation_id,
                event_id=event_id,
                has_data=bool(interaction_data)
            )
            return

        command_name = interaction.get('data', {}).get('name')
        interaction_type = interaction_data.get('interaction_type', 'discord')

        logger.info(
            "Processing Pub/Sub message",
            correlation_id=correlation_id,
            event_id=event_id,
            interaction_type=interaction_type,
            command_name=command_name,
            interaction_id=interaction.get('id')
        )

        logger.debug(
            "Starting command processing",
            correlation_id=correlation_id,
            command_name=command_name
        )

        response = process_interaction(
            interaction, CommandHandler, correlation_id, logger
        )

        if response:
            logger.info(
                "Command processed, sending response",
                correlation_id=correlation_id,
                command_name=command_name,
                response_type=response.get('type') if isinstance(response, dict) else type(response).__name__
            )
        else:
            logger.warning(
                "No response generated for command",
                correlation_id=correlation_id,
                command_name=command_name
            )

        handle_processor_response(interaction_data, response, logger)

        logger.info(
            "Message processed successfully",
            correlation_id=correlation_id,
            command_name=command_name,
            event_id=event_id
        )

    except Exception as e:
        logger.error("Critical error in processor_base_handler", error=e, correlation_id=correlation_id)
        raise
