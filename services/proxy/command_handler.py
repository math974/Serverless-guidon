"""Simple command handlers (ping, hello, help)."""


def handle_simple_command(command_name: str, interaction_type: str = 'discord') -> dict:
    """Handle simple commands that can be processed immediately.

    Args:
        command_name: Name of the command
        interaction_type: 'discord' or 'web'

    Returns:
        Response dict appropriate for the interaction type, or None
    """
    if command_name == 'ping':
        if interaction_type == 'discord':
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Pong!',
                        'description': 'Bot is running with Cloud Run.',
                        'color': 0x00FF00,
                        'footer': {'text': 'Status: Online'}
                    }]
                }
            }
        else:
            return {
                'status': 'success',
                'message': 'Pong!',
                'data': {
                    'service': 'Cloud Run',
                    'status': 'Online'
                }
            }

    elif command_name == 'hello':
        if interaction_type == 'discord':
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Welcome to RATP Service',
                        'description': 'Hello! Welcome to the RATP service. I am your assistant to help you with Paris public transport. How can I help you today?',
                        'color': 0x0066CC,
                        'footer': {'text': 'RATP - Paris Public Transport'}
                    }]
                }
            }
        else:
            return {
                'status': 'success',
                'message': 'Hello! Welcome to the RATP service.',
                'data': {
                    'service': 'RATP - Paris Public Transport',
                    'description': 'I am your assistant to help you with Paris public transport.'
                }
            }

    elif command_name == 'help':
        if interaction_type == 'discord':
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
                        'footer': {'text': 'RATP - Paris Public Transport'}
                    }]
                }
            }
        else:
            return {
                'status': 'success',
                'message': 'Available Commands',
                'data': {
                    'basic_commands': {
                        'hello': 'RATP service greeting',
                        'ping': 'Test bot latency',
                        'help': 'Show this help message'
                    },
                    'art_commands': {
                        'draw': 'Draw a pixel',
                        'snapshot': 'Take a snapshot'
                    }
                }
            }

    return None

