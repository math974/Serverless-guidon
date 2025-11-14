"""Shared application configuration."""
import os


class Config:
    """Application configuration."""
    # Discord configuration
    DISCORD_PUBLIC_KEY = os.environ.get('DISCORD_PUBLIC_KEY')
    DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
    DISCORD_APPLICATION_ID = os.environ.get('DISCORD_APPLICATION_ID')
    AUTO_REGISTER_COMMANDS = os.environ.get('AUTO_REGISTER_COMMANDS', 'true').lower() == 'true'
    DISCORD_API_BASE_URL = "https://discord.com/api/v10"

    # GCP configuration
    PROJECT_ID = os.environ.get('GCP_PROJECT_ID', os.environ.get('GOOGLE_CLOUD_PROJECT'))

    # Pub/Sub configuration
    PUBSUB_TOPIC_DISCORD_INTERACTIONS = os.environ.get(
        'PUBSUB_TOPIC_DISCORD_INTERACTIONS',
        'discord-interactions'
    )
    PUBSUB_TOPIC_DISCORD_COMMANDS_BASE = os.environ.get(
        'PUBSUB_TOPIC_DISCORD_COMMANDS_BASE',
        'discord-commands-base'
    )
    PUBSUB_TOPIC_DISCORD_COMMANDS_ART = os.environ.get(
        'PUBSUB_TOPIC_DISCORD_COMMANDS_ART',
        'discord-commands-art'
    )


# Discord commands definition
# Base commands
BASE_COMMANDS = [
    {
        "name": "hello",
        "description": "RATP service greeting",
        "type": 1
    },
    {
        "name": "ping",
        "description": "Test bot latency",
        "type": 1
    },
    {
        "name": "help",
        "description": "Show available commands",
        "type": 1
    }
]

# Art commands
ART_COMMANDS = [
    {
        "name": "draw",
        "description": "Draw a pixel on the canvas",
        "type": 1,
        "options": [
            {
                "name": "x",
                "description": "X coordinate",
                "type": 4,  # Integer
                "required": True
            },
            {
                "name": "y",
                "description": "Y coordinate",
                "type": 4,  # Integer
                "required": True
            },
            {
                "name": "color",
                "description": "Color in hex format (e.g., #FF0000)",
                "type": 3,  # String
                "required": True
            }
        ]
    },
    {
        "name": "snapshot",
        "description": "Take a snapshot of the current canvas",
        "type": 1
    }
]

# All commands combined (for registration)
COMMANDS = BASE_COMMANDS + ART_COMMANDS

# Command to topic mapping (function to avoid circular reference)
def get_topic_for_command(command_name: str) -> str:
    """Get the Pub/Sub topic for a command."""
    base_commands = ['hello', 'ping', 'help']
    art_commands = ['draw', 'snapshot']

    if command_name in base_commands:
        return Config.PUBSUB_TOPIC_DISCORD_COMMANDS_BASE
    elif command_name in art_commands:
        return Config.PUBSUB_TOPIC_DISCORD_COMMANDS_ART
    else:
        return Config.PUBSUB_TOPIC_DISCORD_COMMANDS_BASE  # Default to base
