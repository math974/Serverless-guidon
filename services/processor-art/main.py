"""Cloud Run service that processes Pub/Sub messages for art Discord commands.
Uses Functions Framework for Cloud Run
"""
import sys
import os
import json
import base64
import requests

# Import shared modules (copied to service directory during deployment)
from shared.observability import init_observability, traced_function
from shared.flask_middleware import add_correlation_middleware

import json
import base64
import requests
from functions_framework import create_app
from command_registry import CommandHandler

app = create_app(__name__)

# Initialize observability
logger, tracing = init_observability('discord-processor-art', app=app)
add_correlation_middleware(app, logger)


def send_response_to_proxy(proxy_url: str, interaction_token: str, application_id: str, response: dict, correlation_id: str = None):
    """Send response to proxy service, which will forward it to Discord."""
    if not proxy_url:
        logger.warning("Proxy URL not provided, cannot send response", correlation_id=correlation_id)
        return False

    url = f"{proxy_url}/discord/response"
    payload = {
        'interaction_token': interaction_token,
        'application_id': application_id,
        'response': response
    }

    try:
        result = requests.post(url, json=payload, timeout=10)
        if result.status_code == 200:
            logger.info(
                "Response sent to proxy",
                correlation_id=correlation_id,
                interaction_token=interaction_token[:10] + "..." if interaction_token else None
            )
            return True
        else:
            logger.error(
                "Error sending response to proxy",
                correlation_id=correlation_id,
                status_code=result.status_code,
                response_text=result.text[:100]
            )
            return False
    except Exception as e:
        logger.error("Exception sending response to proxy", error=e, correlation_id=correlation_id)
        return False


def process_discord_interaction(interaction: dict, correlation_id: str = None) -> dict:
    """Process a Discord interaction and return response."""
    try:
        interaction_type = interaction.get('type')

        if interaction_type == 1:
            logger.debug("PING interaction received", correlation_id=correlation_id)
            return {'type': 1}

        if interaction_type == 2:
            command_name = interaction.get('data', {}).get('name')
            if not command_name:
                logger.error("Missing command name in interaction", correlation_id=correlation_id)
                raise ValueError("Missing command name in interaction data")
            
            logger.info("Processing command", correlation_id=correlation_id, command_name=command_name)
            response = CommandHandler.handle(command_name, interaction)
            logger.info("Command processed successfully", correlation_id=correlation_id, command_name=command_name)
            return response

        logger.warning("Unknown interaction type", correlation_id=correlation_id, interaction_type=interaction_type)
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Unknown Interaction Type',
                    'description': 'This interaction type is not supported.',
                    'color': 0xFF0000
                }]
            }
        }
    except Exception as e:
        logger.error("Error processing interaction", error=e, correlation_id=correlation_id)

        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Processing Error',
                    'description': 'An unexpected error occurred. The service is still running.',
                    'color': 0xFF0000,
                    'footer': {
                        'text': 'Error logged - service continues running'
                    }
                }]
            }
        }


@app.route("/", methods=['POST'])
@traced_function("process_pubsub_message")
def process_pubsub_message(request):
    """Process Pub/Sub push message."""
    correlation_id = None
    
    try:
        envelope = request.get_json(silent=True)

        if not envelope:
            logger.warning("Missing envelope in Pub/Sub message")
            return {'status': 'error', 'message': 'Missing envelope'}, 400

        pubsub_message = envelope.get('message', {})
        if not pubsub_message:
            logger.warning("Missing message in Pub/Sub envelope")
            return {'status': 'error', 'message': 'Missing envelope'}, 400

        pubsub_message = envelope.get('message', {})
        if not pubsub_message:
            return {'status': 'error', 'message': 'Missing message'}, 400

        try:
            message_data = base64.b64decode(pubsub_message.get('data', '')).decode('utf-8')
            interaction_data = json.loads(message_data)
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            logger.error("Error decoding Pub/Sub message", error=e)
            return {'status': 'error', 'message': 'Invalid message format'}, 400

        # Extract correlation ID from message
        correlation_id = interaction_data.get('correlation_id', 'unknown')
        
        interaction = interaction_data.get('interaction', {})
        if not interaction:
            logger.warning("Missing interaction in message", correlation_id=correlation_id)
            return {'status': 'error', 'message': 'Missing interaction'}, 400

        proxy_url = interaction_data.get('proxy_url')
        interaction_type = interaction_data.get('interaction_type', 'discord')
        
        logger.info(
            "Processing Pub/Sub message",
            correlation_id=correlation_id,
            interaction_type=interaction_type,
            command_name=interaction.get('data', {}).get('name')
        )
        
        response = process_discord_interaction(interaction, correlation_id)

        interaction_token = interaction.get('token')
        application_id = interaction.get('application_id')

        if interaction_type == 'web' and proxy_url:
            try:
                web_response_url = f"{proxy_url}/web/response"
                web_payload = {
                    'token': interaction_token,
                    'response': response
                }
                requests.post(web_response_url, json=web_payload, timeout=10)
                logger.info("Sent web response", correlation_id=correlation_id)
            except Exception as e:
                logger.error("Error sending web response", error=e, correlation_id=correlation_id)
        elif interaction_token and application_id and proxy_url:
            try:
                send_response_to_proxy(proxy_url, interaction_token, application_id, response, correlation_id)
            except Exception as e:
                logger.error("Error sending response to proxy", error=e, correlation_id=correlation_id)

        logger.info("Message processed successfully", correlation_id=correlation_id)
        return {'status': 'processed'}, 200

    except Exception as e:
        logger.error("Critical error in process_pubsub_message", error=e, correlation_id=correlation_id)
        return {'status': 'processed'}, 200

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {'status': 'error', 'message': 'Internal error (logged)'}, 200


@app.route("/health", methods=['GET'])
def health(request):
    """Health check endpoint."""
    logger.info("Health check called", correlation_id=getattr(g, 'correlation_id', None))
    return {
        'status': 'healthy',
        'service': 'discord-processor-art',
        'handlers': list(CommandHandler.HANDLERS.keys())
    }, 200
