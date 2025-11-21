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
    return None

