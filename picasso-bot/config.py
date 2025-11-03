"""Application configuration."""
import os


class Config:
    """Application configuration."""
    DISCORD_PUBLIC_KEY = os.environ.get('DISCORD_PUBLIC_KEY')
    DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
    DISCORD_APPLICATION_ID = os.environ.get('DISCORD_APPLICATION_ID')
    AUTO_REGISTER_COMMANDS = os.environ.get('AUTO_REGISTER_COMMANDS', 'true').lower() == 'true'
    DISCORD_API_BASE_URL = "https://discord.com/api/v10"


# Discord commands definition
COMMANDS = [
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

