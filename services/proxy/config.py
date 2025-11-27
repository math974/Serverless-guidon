"""Configuration and constants for the proxy service."""
import os

PROJECT_ID = os.environ.get('GCP_PROJECT_ID', os.environ.get('GOOGLE_CLOUD_PROJECT'))
DISCORD_PUBLIC_KEY = os.environ.get('DISCORD_PUBLIC_KEY')
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
DISCORD_APPLICATION_ID = os.environ.get('DISCORD_APPLICATION_ID')
DISCORD_API_BASE_URL = "https://discord.com/api/v10"
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', '').rstrip('/')

PUBSUB_TOPIC_INTERACTIONS = os.environ.get(
    'PUBSUB_TOPIC_INTERACTIONS', 'interactions'
)
PUBSUB_TOPIC_COMMANDS_BASE = os.environ.get(
    'PUBSUB_TOPIC_COMMANDS_BASE', 'commands-base'
)

