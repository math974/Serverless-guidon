"""Serverless function to register Discord commands."""
import json
from config import Config, COMMANDS
from discord_service import DiscordService


def register_commands(request):
    """
    Serverless function to register Discord commands.
    
    Args:
        request: Flask/Cloud Functions request object
        
    Returns:
        tuple: (response_data, status_code) or Flask Response
    """
    # Check that it's a POST request
    if request.method != 'POST':
        return json.dumps({'error': 'Method not allowed'}), 405
    
    # Check configuration
    if not Config.DISCORD_BOT_TOKEN or not Config.DISCORD_APPLICATION_ID:
        return json.dumps({
            'error': 'DISCORD_BOT_TOKEN and DISCORD_APPLICATION_ID must be configured'
        }), 500
    
    # Register all commands
    results = []
    for command in COMMANDS:
        result = DiscordService.register_command(command)
        results.append({
            'command': command['name'],
            **result
        })
    
    response_data = {
        'message': 'Registration completed',
        'results': results,
        'note': 'Commands may take a few minutes to appear in Discord'
    }
    
    return json.dumps(response_data), 200

