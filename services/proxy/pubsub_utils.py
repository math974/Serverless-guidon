"""Pub/Sub utilities."""
import json
from google.cloud import pubsub_v1

from config import PROJECT_ID, PUBSUB_TOPIC_DISCORD_COMMANDS_ART, PUBSUB_TOPIC_DISCORD_COMMANDS_BASE

publisher = pubsub_v1.PublisherClient()


def get_topic_for_command(command_name: str) -> str:
    """Get Pub/Sub topic for a command."""
    art_commands = ['draw', 'snapshot']
    if command_name in art_commands:
        return PUBSUB_TOPIC_DISCORD_COMMANDS_ART
    return PUBSUB_TOPIC_DISCORD_COMMANDS_BASE


def publish_to_pubsub(topic_name: str, data: dict) -> str:
    """Publish message to Pub/Sub topic."""
    try:
        if not PROJECT_ID:
            raise ValueError("PROJECT_ID not configured")

        topic_path = publisher.topic_path(PROJECT_ID, topic_name)
        message_data = json.dumps(data).encode('utf-8')
        future = publisher.publish(topic_path, message_data)
        message_id = future.result(timeout=10)

        return message_id
    except Exception as e:
        print(f"ERROR publishing to Pub/Sub topic {topic_name}: {e}")
        raise

