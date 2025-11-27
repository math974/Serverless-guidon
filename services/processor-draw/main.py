"""Cloud Functions service that processes Pub/Sub messages for draw command."""
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

logger, tracing = init_observability('processor-draw', app=None)


@cloud_event
@traced_function("processor_draw_handler")
def processor_draw_handler(cloud_event: CloudEvent):
    """Process Pub/Sub message from CloudEvent."""
    correlation_id = None

    try:
        message_data = cloud_event.data
        event_id = getattr(cloud_event, 'id', None)

        if not message_data:
            logger.warning("Missing data in CloudEvent", event_id=event_id)
            return

        try:
            if isinstance(message_data.get('message', {}).get('data'), str):
                encoded_data = message_data['message']['data']
                decoded_data = base64.b64decode(encoded_data).decode('utf-8')
                interaction_data = json.loads(decoded_data)
            else:
                interaction_data = message_data
        except (ValueError, TypeError, json.JSONDecodeError, KeyError) as e:
            logger.error("Error decoding Pub/Sub message", error=e, event_id=event_id)
            return

        correlation_id = interaction_data.get('correlation_id', 'unknown')
        interaction = interaction_data.get('interaction', {})

        if not interaction:
            logger.warning("Missing interaction in message", correlation_id=correlation_id, event_id=event_id)
            return

        command_name = interaction.get('data', {}).get('name')
        interaction_type = interaction_data.get('interaction_type', 'discord')

        logger.info(
            "Processing draw command",
            correlation_id=correlation_id,
            event_id=event_id,
            interaction_type=interaction_type,
            command_name=command_name
        )

        response = process_interaction(
            interaction, CommandHandler, correlation_id, logger
        )

        if response:
            logger.info("Draw command processed, sending response", correlation_id=correlation_id, command_name=command_name)
        else:
            logger.warning("No response generated for draw command", correlation_id=correlation_id, command_name=command_name)

        handle_processor_response(interaction_data, response, logger)

        logger.info("Draw message processed successfully", correlation_id=correlation_id, command_name=command_name, event_id=event_id)

    except Exception as e:
        logger.error("Critical error in processor_draw_handler", error=e, correlation_id=correlation_id)
        raise

