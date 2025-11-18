"""Base Discord commands (ping, hello, help)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from command_registry import CommandHandler  # noqa: E402
from shared.embed_utils import (  # noqa: E402
    create_info_embed,
    create_success_embed,
)

@CommandHandler.register('hello')
def handle_hello():
    """Handle hello command."""
    return create_info_embed(
        title='Welcome to Picasso Service',
        description='Hello! Welcome to the Picasso service. I am your assistant to help you create art on the canvas. How can I help you today?',
        footer={'text': 'Picasso - Art Bot'}
    )


@CommandHandler.register('ping')
def handle_ping():
    """Handle ping command."""
    return create_success_embed(
        title='Pong!',
        description='Bot is running with Cloud Run.',
        footer={'text': 'Status: Online'}
    )

@CommandHandler.register('help')
def handle_help():
    """Handle help command."""
    web_frontend_url = os.environ.get('WEB_FRONTEND_URL', '').strip()

    description = 'Here are all the commands you can use:'
    if web_frontend_url:
        description += f'\n\n**Web Interface:** {web_frontend_url}'

    return create_info_embed(
        title='Help - Available Commands',
        description=description,
        fields=[
            {
                'name': 'Basic Commands',
                'value': '`/hello` - Picasso service greeting\n`/ping` - Test bot latency\n`/help` - Show this help message',
                'inline': False
            },
            {
                'name': 'Art Commands',
                'value': '`/draw <x> <y> <color>` - Draw a pixel\n`/snapshot` - Take a canvas snapshot\n`/stats` - Show your statistics\n`/colors` - List available colors',
                'inline': False
            },
            {
                'name': 'User Commands',
                'value': '`/register` - Register your account\n`/userinfo [user]` - Show user info (optional user)\n`/leaderboard` - Top 10 users',
                'inline': False
            },
            {
                'name': 'Admin Commands',
                'value': '`/ban <user> [reason]` - Ban a user\n`/unban <user>` - Unban a user\n`/setpremium <user> <true/false>` - Set premium status',
                'inline': False
            }
        ],
        footer={'text': 'Picasso - Art Bot'}
    )

