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
                        'description': 'Bot is running with Functions Framework.',
                        'color': 0x00FF00,
                        'footer': {'text': 'Picasso - Art Bot'}
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
                        'title': 'Welcome to Picasso Service',
                        'description': 'Hello! Welcome to the Picasso service. I am your brush to create art. How can I help you today?',
                        'color': 0x0066CC,
                        'footer': {'text': 'Picasso - Art Bot'}
                    }]
                }
            }
        else:
            return {
                'status': 'success',
                'message': 'Hello! Welcome to the Picasso service. I am your brush to create art.',
                'data': {
                    'service': 'Picasso - Art Bot',
                    'description': 'I am your brush to create art.'
                }
            }

    elif command_name == 'help':
        if interaction_type == 'discord':
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Available Commands',
                        'description': 'Here are the commands you can use to create art:',
                        'color': 0x0066CC,
                        'fields': [
                            {
                                'name': 'Basic Commands',
                                'value': '`/hello` - Picasso service greeting\n`/ping` - Test bot latency\n`/help` - Show this help message to see all commands',
                                'inline': False
                            },
                            {
                                'name': 'Art Commands',
                                'value': '`/draw` - Draw a pixel\n`/snapshot` - Take a snapshot of the current canvas',
                                'inline': False
                            }
                        ],
                        'footer': {'text': 'Picasso - Art Bot'}
                    }]
                }
            }
        else:
            return {
                'status': 'success',
                'message': 'Available Commands to create art:',
                'data': {
                    'basic_commands': {
                        'hello': 'Picasso service greeting to start the conversation',
                        'ping': 'Test bot latency to check if the bot is running',
                        'help': 'Show this help message to see all commands'
                    },
                    'art_commands': {
                        'draw': 'Draw a pixel on the canvas',
                        'snapshot': 'Take a snapshot of the current canvas'
                    }
                }
            }

    return None

