"""Base Discord commands (ping, hello, help)."""
from datetime import datetime, timezone
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from command_registry import CommandHandler  # noqa: E402


@CommandHandler.register('hello')
def handle_hello():
    """Handle hello command."""
    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': 'Welcome to Picasso Service',
                'description': 'Hello! Welcome to the Picasso service. I am your assistant to help you create art on the canvas. How can I help you today?',
                'color': 0x0066CC,
                'footer': {
                    'text': 'Picasso - Art Bot'
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }]
        }
    }


@CommandHandler.register('ping')
def handle_ping():
    """Handle ping command."""
    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': 'Pong!',
                'description': 'Bot is running with Cloud Run.',
                'color': 0x00FF00,
                'footer': {
                    'text': 'Status: Online'
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }]
        }
    }


@CommandHandler.register('help')
def handle_help():
    """Handle help command."""
    return {
        'type': 4,
        'data': {
            'embeds': [
                {
                    'title': '📚 Available Commands',
                    'description': 'Here are all the commands you can use:',
                    'color': 0x0066CC,
                    'fields': [
                        {
                            'name': '🔷 Basic Commands',
                            'value': '`/hello` - Picasso service greeting\n`/ping` - Test bot latency\n`/help` - Show this help message',
                            'inline': False
                        },
                        {
                            'name': '🎨 Art Commands',
                            'value': '`/draw <x> <y> <color>` - Draw a pixel\n`/snapshot` - Take a canvas snapshot',
                            'inline': False
                        },
                        {
                            'name': '👤 User Commands',
                            'value': '`/register` - Register your account\n`/stats` - Your statistics\n`/userinfo [user]` - Show user info (optional user)\n`/leaderboard` - Top 10 users',
                            'inline': False
                        },
                        {
                            'name': '🛡️ Admin Commands',
                            'value': '`/ban <user> [reason]` - Ban a user\n`/unban <user>` - Unban a user\n`/setpremium <user> <true/false>` - Set premium status',
                            'inline': False
                        }
                    ],
                    'footer': {
                        'text': 'Picasso - Art Bot'
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            ]
        }
    }

