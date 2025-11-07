"""Serverless function for health check."""
import json
from datetime import datetime
from config import Config


def health_check(request):
    """
    Serverless function for health check.
    
    Args:
        request: Flask/Cloud Functions request object
        
    Returns:
        tuple: (response_data, status_code) or Flask Response
    """
    # Accept GET and OPTIONS (for CORS)
    if request.method not in ['GET', 'OPTIONS']:
        return json.dumps({'error': 'Method not allowed'}), 405
    
    if request.method == 'OPTIONS':
        # Handle CORS preflight requests
        return '', 200
    
    response_data = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'discord-bot',
        'environment': {
            'public_key_set': bool(Config.DISCORD_PUBLIC_KEY),
            'bot_token_set': bool(Config.DISCORD_BOT_TOKEN),
            'app_id_set': bool(Config.DISCORD_APPLICATION_ID)
        }
    }
    
    return json.dumps(response_data), 200

