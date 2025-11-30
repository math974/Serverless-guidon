"""Shared utilities for processor services."""
import os
import requests
from typing import Optional, Dict

def get_auth_token(audience: str, logger=None) -> Optional[str]:
    """Get Google Cloud identity token for service-to-service authentication.

    Args:
        audience: The target service URL (audience for the token)
        logger: Optional logger instance for error logging

    Returns:
        Identity token string or None if failed
    """
    if not audience:
        if logger:
            logger.warning("Audience URL not provided for identity token")
        return None

    try:
        from urllib.parse import urlparse
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        parsed = urlparse(audience)
        normalized_audience = f"{parsed.scheme}://{parsed.netloc}"

        if logger:
            logger.debug(
                "Normalizing audience for identity token",
                original_audience=audience,
                normalized_audience=normalized_audience
            )

        request_session = google_requests.Request()
        token = id_token.fetch_id_token(request_session, normalized_audience)
        return token
    except Exception as e:
        if logger:
            logger.warning(
                "Failed to get identity token",
                error=e,
                audience=audience
            )
        return None


def verify_auth_token(request, expected_audience: str = None, logger=None) -> tuple[bool, Optional[str]]:
    """Verify Google Cloud identity token from request headers.

    Args:
        request: Flask request object
        expected_audience: Optional expected audience (service URL)
        logger: Optional logger instance for error logging

    Returns:
        Tuple of (is_valid: bool, error_message: str or None)
    """
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return False, "Missing or invalid Authorization header"

    token = auth_header[7:]  # Remove 'Bearer ' prefix

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        request_session = google_requests.Request()

        # Verify token
        claims = id_token.verify_token(token, request_session, audience=expected_audience)

        if logger:
            logger.debug(
                "Token verified successfully",
                email=claims.get('email'),
                audience=claims.get('aud')
            )

        return True, None
    except ValueError as e:
        if logger:
            logger.warning("Invalid token", error=e)
        return False, f"Invalid token: {str(e)}"
    except Exception as e:
        if logger:
            logger.error("Error verifying token", error=e)
        return False, f"Token verification error: {str(e)}"


def get_authenticated_headers(audience: str, correlation_id: Optional[str] = None, logger=None) -> Dict[str, str]:
    """Get headers with authentication token for service-to-service calls.

    Args:
        audience: Target service URL (audience for the token)
        correlation_id: Optional correlation ID for logging
        logger: Optional logger instance

    Returns:
        Dictionary with headers including Authorization
    """
    headers = {}
    if correlation_id:
        headers['X-Correlation-ID'] = correlation_id

    auth_token = get_auth_token(audience, logger)
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'

    return headers


def send_discord_webhook_direct(
    interaction_token: str,
    application_id: str,
    response: dict,
    discord_bot_token: str,
    correlation_id: Optional[str] = None,
    logger=None
) -> bool:
    """Send response directly to Discord webhook.

    Args:
        interaction_token: Discord interaction token
        application_id: Discord application ID
        response: Response dict to send
        discord_bot_token: Discord bot token
        correlation_id: Optional correlation ID for logging
        logger: Logger instance (optional)

    Returns:
        True if successful, False otherwise
    """
    if not discord_bot_token:
        if logger:
            logger.warning("Discord bot token not provided", correlation_id=correlation_id)
        return False

    if not interaction_token or not application_id:
        if logger:
            logger.warning("Missing Discord interaction token or application ID", correlation_id=correlation_id)
        return False

    url = f"https://discord.com/api/v10/webhooks/{application_id}/{interaction_token}"
    headers = {
        "Authorization": f"Bot {discord_bot_token}",
        "Content-Type": "application/json"
    }

    # Extract payload from response
    if 'data' in response:
        payload = response['data']
    elif 'type' in response and 'data' in response:
        payload = response['data']
    else:
        payload = response

    # Validate payload has content
    has_content = bool(payload.get('content'))
    has_embeds = bool(payload.get('embeds'))
    if not has_content and not has_embeds:
        if logger:
            logger.warning("Response has no content or embeds", correlation_id=correlation_id)
        return False

    try:
        result = requests.post(url, headers=headers, json=payload, timeout=10)
        if result.status_code in [200, 204]:
            if logger:
                logger.info(
                    "Response sent directly to Discord webhook",
                    correlation_id=correlation_id,
                    application_id=application_id
                )
            return True
        else:
            if logger:
                logger.error(
                    "Error sending to Discord webhook",
                    correlation_id=correlation_id,
                    status_code=result.status_code,
                    response_text=result.text[:200]
                )
            return False
    except Exception as e:
        if logger:
            logger.error("Exception sending to Discord webhook", error=e, correlation_id=correlation_id)
        return False


def send_web_webhook(
    webhook_url: str,
    response: dict,
    correlation_id: Optional[str] = None,
    logger=None
) -> bool:
    """Send response directly to web webhook URL.

    Args:
        webhook_url: Webhook URL to send response to
        response: Response dict to send
        correlation_id: Optional correlation ID for logging
        logger: Logger instance (optional)

    Returns:
        True if successful, False otherwise
    """
    if not webhook_url:
        if logger:
            logger.warning("Webhook URL not provided", correlation_id=correlation_id)
        return False

    try:
        result = requests.post(webhook_url, json=response, timeout=10)
        if result.status_code in [200, 201, 204]:
            if logger:
                logger.info("Response sent directly to web webhook", correlation_id=correlation_id)
            return True
        else:
            if logger:
                logger.error(
                    "Error sending to web webhook",
                    correlation_id=correlation_id,
                    status_code=result.status_code,
                    response_text=result.text[:200]
                )
            return False
    except Exception as e:
        if logger:
            logger.error("Exception sending to web webhook", error=e, correlation_id=correlation_id)
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

    user_manager_url = user_manager_url.rstrip('/')
    if not user_manager_url.startswith('http://') and not user_manager_url.startswith('https://'):
        user_manager_url = f"https://{user_manager_url}"
    elif user_manager_url.startswith('http://'):
        user_manager_url = user_manager_url.replace('http://', 'https://', 1)

    headers = get_authenticated_headers(user_manager_url, correlation_id, logger)
    headers['Content-Type'] = 'application/json'

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


def process_interaction(
    interaction: dict,
    command_handler,
    correlation_id: Optional[str] = None,
    logger=None
) -> dict:
    """Process a Discord or Web interaction and return response.

    Args:
        interaction: Interaction dict (Discord format or Web format converted to Discord-like)
        command_handler: CommandHandler instance with HANDLERS attribute
        correlation_id: Optional correlation ID for logging
        logger: Logger instance (optional)

    Returns:
        Interaction response dict (Discord format or Web format)
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
            interaction_with_context = interaction.copy()
            if correlation_id:
                interaction_with_context['correlation_id'] = correlation_id
            response = command_handler.handle(command_name, interaction_with_context)
            read_only_commands = {
                'stats', 'leaderboard', 'canvas-state', 'snapshot',
                'colors', 'pixel-info', 'hello', 'ping', 'help', 'userinfo'
            }
            self_managed_commands = {
                'draw'
            }

            member = interaction.get('member')
            user = (member.get('user') if member else None) or interaction.get('user')
            if user:
                user_id = user.get('id')
                if user_id and command_name not in read_only_commands and command_name not in self_managed_commands:
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

