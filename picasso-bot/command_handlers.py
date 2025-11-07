"""Handlers for Discord slash commands."""
from command_registry import CommandHandler
from datetime import datetime
import json
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("serverless-ejguidon-dev", "discord")

@CommandHandler.register('hello')
def handle_hello():
    """Handle hello command."""
    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': 'Welcome to RATP Service',
                'description': 'Hello! Welcome to the RATP service. I am your assistant to help you with Paris public transport. How can I help you today?',
                'color': 0x0066CC,  # RATP blue color
                'footer': {
                    'text': 'RATP - Paris Public Transport'
                },
                'timestamp': datetime.utcnow().isoformat()
            }]
        }
    }

@CommandHandler.register('draw')
def handle_draw():
    """Handle draw command."""
    try:
        data = {"message": "Draw Pub/Sub!"}
        data_str = json.dumps(data)
        data_bytes = data_str.encode("utf-8")
        future = publisher.publish(topic_path, data=data_bytes)
        future.result()
    except Exception as e:
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Error',
                    'description': f'Failed to publish message: {str(e)}',
                    'color': 0xFF0000,
                    'timestamp': datetime.utcnow().isoformat()
                }]
            }
        }

    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': 'Welcome to Draw Service',
                'description': 'Hello! Welcome to the Draw service. You can now draw using the Pub/Sub integration.',
                'color': 0x0066CC,
                'footer': {
                    'text': 'Draw - Paris Public Transport'
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
                'color': 0x00FF00,  # Green color
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
                'color': 0x0066CC,  # RATP blue color
                'fields': [
                    {
                        'name': '/hello',
                        'value': 'RATP service greeting',
                        'inline': True
                    },
                    {
                        'name': '/ping',
                        'value': 'Test bot latency',
                        'inline': True
                    },
                    {
                        'name': '/help',
                        'value': 'Show this help message',
                        'inline': True
                    }
                ],
                'footer': {
                    'text': 'RATP - Paris Public Transport'
                },
                'timestamp': datetime.utcnow().isoformat()
            }]
        }
    }

