"""Base Discord commands (ping, hello, help)."""
from datetime import datetime
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
                'title': 'Welcome to RATP Service',
                'description': 'Hello! Welcome to the RATP service. I am your assistant to help you with Paris public transport. How can I help you today?',
                'color': 0x0066CC,
                'footer': {
                    'text': 'RATP - Paris Public Transport'
                },
                'timestamp': datetime.utcnow().isoformat()
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
                'timestamp': datetime.utcnow().isoformat()
            }]
        }
    }


@CommandHandler.register('help')
def handle_help():
    """Handle help command."""
    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': 'Available Commands',
                'description': 'Here are the commands you can use:',
                'color': 0x0066CC,
                'fields': [
                    {
                        'name': 'Basic Commands',
                        'value': '`/hello` - RATP service greeting\n`/ping` - Test bot latency\n`/help` - Show this help message',
                        'inline': False
                    },
                    {
                        'name': 'Art Commands',
                        'value': '`/draw` - Draw a pixel\n`/snapshot` - Take a snapshot',
                        'inline': False
                    }
                ],
                'footer': {
                    'text': 'RATP - Paris Public Transport'
                },
                'timestamp': datetime.utcnow().isoformat()
            }]
        }
    }

