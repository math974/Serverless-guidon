"""Shared utilities for processor services."""
import os
import requests
from typing import Optional

def send_response_to_proxy(
    proxy_url: str,
    interaction_token: str,
    application_id: str,
    response: dict,
    correlation_id: Optional[str] = None,
    logger=None
) -> bool:
    """Send response to proxy service, which will forward it to Discord.

    Args:
        proxy_url: URL of the proxy service
        interaction_token: Discord interaction token
        application_id: Discord application ID
        response: Response dict to send
        correlation_id: Optional correlation ID for logging
        logger: Logger instance (optional)

    Returns:
        True if successful, False otherwise
    """
    if not proxy_url:
        if logger:
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
            if logger:
                logger.info(
                    "Response sent to proxy",
                    correlation_id=correlation_id,
                    interaction_token=interaction_token[:10] + "..." if interaction_token else None
                )
            return True
        else:
            if logger:
                logger.error(
                    "Error sending response to proxy",
                    correlation_id=correlation_id,
                    status_code=result.status_code,
                    response_text=result.text[:100]
                )
            return False
    except Exception as e:
        if logger:
            logger.error("Exception sending response to proxy", error=e, correlation_id=correlation_id)
        return False


def send_web_response(
    proxy_url: str,
    token: str,
    response: dict,
    correlation_id: Optional[str] = None,
    logger=None
) -> bool:
    """Send response to proxy service for web interactions.

    Args:
        proxy_url: URL of the proxy service
        token: Interaction token
        response: Response dict to send
        correlation_id: Optional correlation ID for logging
        logger: Logger instance (optional)

    Returns:
        True if successful, False otherwise
    """
    if not proxy_url:
        if logger:
            logger.warning("Proxy URL not provided, cannot send web response", correlation_id=correlation_id)
        return False

    url = f"{proxy_url}/web/response"
    payload = {
        'token': token,
        'response': response
    }

    try:
        result = requests.post(url, json=payload, timeout=10)
        if result.status_code == 200:
            if logger:
                logger.info("Sent web response", correlation_id=correlation_id)
            return True
        else:
            if logger:
                logger.error(
                    "Error sending web response",
                    correlation_id=correlation_id,
                    status_code=result.status_code
                )
            return False
    except Exception as e:
        if logger:
            logger.error("Error sending web response", error=e, correlation_id=correlation_id)
        return False


def increment_user_usage_async(
    user_id: str,
    command: str,
    correlation_id: Optional[str] = None,
    logger=None
):
    """Increment user usage counter asynchronously (non-blocking).

    Args:
        user_id: Discord user ID
        command: Command name
        correlation_id: Optional correlation ID for logging
        logger: Logger instance (optional)
    """
    user_manager_url = os.environ.get('USER_MANAGER_URL')
    if not user_manager_url:
        return

    # Get Google Cloud identity token for authentication
    auth_token = None
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        request_session = google_requests.Request()
        target_audience = user_manager_url
        auth_token = id_token.fetch_id_token(request_session, target_audience)
    except Exception as e:
        if logger:
            logger.warning(
                "Failed to get identity token for user-manager",
                error=e,
                correlation_id=correlation_id
            )
        return

    headers = {}
    if correlation_id:
        headers['X-Correlation-ID'] = correlation_id
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'

    try:
        response = requests.post(
            f"{user_manager_url}/api/users/{user_id}/increment",
            json={'command': command},
            headers=headers,
            timeout=2
        )
        if response.status_code == 200 and logger:
            logger.debug(
                "User usage incremented",
                correlation_id=correlation_id,
                user_id=user_id,
                command=command
            )
        elif response.status_code != 200 and logger:
            logger.warning(
                "Failed to increment user usage",
                correlation_id=correlation_id,
                user_id=user_id,
                status_code=response.status_code,
                response_text=response.text[:200]
            )
    except Exception as e:
        # Non-blocking, just log warning
        if logger:
            logger.warning(
                "Failed to increment user usage (non-blocking)",
                error=e,
                correlation_id=correlation_id,
                user_id=user_id
            )


def process_discord_interaction(
    interaction: dict,
    command_handler,
    correlation_id: Optional[str] = None,
    logger=None
) -> dict:
    """Process a Discord interaction and return response.

    Args:
        interaction: Discord interaction dict
        command_handler: CommandHandler instance with HANDLERS attribute
        correlation_id: Optional correlation ID for logging
        logger: Logger instance (optional)

    Returns:
        Discord interaction response dict
    """
    try:
        interaction_type = interaction.get('type')

        if interaction_type == 1:
            if logger:
                logger.debug("PING interaction received", correlation_id=correlation_id)
            return {'type': 1}

        if interaction_type == 2:
            command_name = interaction.get('data', {}).get('name')
            if not command_name:
                if logger:
                    logger.error("Missing command name in interaction", correlation_id=correlation_id)
                raise ValueError("Missing command name in interaction data")

            if logger:
                logger.info("Processing command", correlation_id=correlation_id, command_name=command_name)
            response = command_handler.handle(command_name, interaction)

            # Increment user usage after successful command processing (non-blocking)
            member = interaction.get('member')
            user = (member.get('user') if member else None) or interaction.get('user')
            if user:
                user_id = user.get('id')
                if user_id:
                    increment_user_usage_async(user_id, command_name, correlation_id=correlation_id, logger=logger)

            if logger:
                logger.info("Command processed successfully", correlation_id=correlation_id, command_name=command_name)
            return response

        if logger:
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
        if logger:
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

