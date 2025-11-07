"""Main serverless function for Discord interactions."""
import json
from datetime import datetime
from config import Config
from discord_service import DiscordService
from interaction_handler import InteractionHandler
import command_handlers  # Import to register handlers


def discord_interactions(request):
    """
    Serverless function to handle Discord interactions.
    
    Args:
        request: Flask/Cloud Functions request object
        
    Returns:
        tuple: (response_data, status_code) or Flask Response
    """
    # Check that it's a POST request
    if request.method != 'POST':
        return json.dumps({'error': 'Method not allowed'}), 405
    
    # Get signature headers
    signature = request.headers.get('X-Signature-Ed25519')
    timestamp = request.headers.get('X-Signature-Timestamp')
    
    if not signature or not timestamp:
        return json.dumps({'error': 'Bad Request - Missing headers'}), 400
    
    # Verify signature
    body = request.get_data()
    if not DiscordService.verify_signature(signature, timestamp, body):
        return json.dumps({'error': 'Unauthorized'}), 401
    
    # Parse JSON
    try:
        interaction = request.get_json()
    except Exception:
        return json.dumps({'error': 'Bad Request - Invalid JSON'}), 400
    
    # Process interaction
    response, status_code = InteractionHandler.process(interaction)
    return json.dumps(response), status_code
