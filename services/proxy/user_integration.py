"""Integration with user-manager service for rate limiting and user management."""
import os
import requests
from typing import Optional, Dict, Tuple
from shared.observability import init_observability

logger, _ = init_observability('discord-proxy', app=None)

# User manager service URL
USER_MANAGER_URL = os.environ.get('USER_MANAGER_URL', '')


def get_auth_token() -> Optional[str]:
    """Get Google Cloud identity token for calling user-manager."""
    if not USER_MANAGER_URL:
        return None
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        request_session = google_requests.Request()
        target_audience = USER_MANAGER_URL
        return id_token.fetch_id_token(request_session, target_audience)
    except Exception as e:
        logger.warning("Failed to get identity token for user-manager", error=e)
        return None


def get_user_id_from_interaction(interaction: dict) -> Optional[str]:
    """Extract user ID from Discord interaction.

    Args:
        interaction: Discord interaction data

    Returns:
        User ID string or None
    """
    member = interaction.get('member')
    if member:
        return member.get('user', {}).get('id')

    user = interaction.get('user')
    if user:
        return user.get('id')

    return None


def is_user_registered(
    user_id: str,
    correlation_id: Optional[str] = None
) -> bool:
    """Check if user is registered in the system.

    Args:
        user_id: Discord user ID
        correlation_id: Correlation ID for logging

    Returns:
        True if user is registered, False otherwise
    """
    if not USER_MANAGER_URL:
        return False

    try:
        auth_token = get_auth_token()
        headers = {}
        if correlation_id:
            headers['X-Correlation-ID'] = correlation_id
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'

        user_response = requests.get(
            f"{USER_MANAGER_URL}/api/users/{user_id}",
            headers=headers,
            timeout=2
        )

        return user_response.status_code == 200
    except Exception as e:
        logger.warning(
            "Error checking if user is registered",
            error=e,
            correlation_id=correlation_id,
            user_id=user_id
        )
        return False


def check_user_allowed(
    user_id: str,
    command: str,
    correlation_id: Optional[str] = None,
    user_payload: Optional[Dict] = None
) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Check if user is allowed to execute command (not banned, rate limit OK).

    Args:
        user_id: Discord user ID
        command: Command name
        correlation_id: Correlation ID for logging

    Returns:
        Tuple of (allowed: bool, rate_limit_info: dict or None, error_message: str or None)
    """
    if not USER_MANAGER_URL:
        logger.warning(
            "USER_MANAGER_URL not configured, skipping user checks",
            correlation_id=correlation_id,
            user_id=user_id,
            command=command
        )
        return True, None, None

    try:
        # Get authentication token
        auth_token = get_auth_token()
        headers = {}
        if correlation_id:
            headers['X-Correlation-ID'] = correlation_id
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'

        # First, get user to check if banned and get premium status
        user_response = requests.get(
            f"{USER_MANAGER_URL}/api/users/{user_id}",
            headers=headers,
            timeout=2
        )

        is_premium = False
        if user_response.status_code == 200:
            user_data = user_response.json()
            if user_data.get('is_banned'):
                logger.warning(
                    "Banned user attempted command",
                    correlation_id=correlation_id,
                    user_id=user_id,
                    command=command
                )
                return False, None, "User is banned"
            is_premium = user_data.get('is_premium', False)
        elif user_response.status_code == 404:
            logger.debug(
                "User not found",
                correlation_id=correlation_id,
                user_id=user_id
            )
            # Don't auto-create here, user must register first
        else:
            # Error getting user, allow but log
            logger.warning(
                "Error getting user, allowing command",
                correlation_id=correlation_id,
                user_id=user_id,
                status_code=user_response.status_code
            )

        # Check rate limit
        rate_limit_response = requests.post(
            f"{USER_MANAGER_URL}/api/rate-limit/check",
            json={
                'user_id': user_id,
                'command': command,
                'is_premium': is_premium
            },
            headers=headers,
            timeout=2
        )

        if rate_limit_response.status_code == 429:
            # Rate limit exceeded
            rate_limit_info = rate_limit_response.json()
            logger.warning(
                "Rate limit exceeded",
                correlation_id=correlation_id,
                user_id=user_id,
                command=command,
                remaining=rate_limit_info.get('remaining', 0),
                reset_in=rate_limit_info.get('reset_in', 0)
            )
            return False, rate_limit_info, f"Rate limit exceeded. Try again in {rate_limit_info.get('reset_in', 0)} seconds"
        elif rate_limit_response.status_code == 200:
            rate_limit_info = rate_limit_response.json()
            logger.debug(
                "Rate limit check passed",
                correlation_id=correlation_id,
                user_id=user_id,
                command=command,
                remaining=rate_limit_info.get('remaining', 0)
            )
            return True, rate_limit_info, None
        else:
            # Error checking rate limit, allow but log
            logger.warning(
                "Error checking rate limit, allowing command",
                correlation_id=correlation_id,
                user_id=user_id,
                status_code=rate_limit_response.status_code
            )
            return True, None, None

    except requests.exceptions.Timeout:
        logger.warning(
            "Timeout checking user manager, allowing command",
            correlation_id=correlation_id,
            user_id=user_id,
            command=command
        )
        return True, None, None
    except Exception as e:
        logger.error(
            "Error checking user manager, allowing command",
            error=e,
            correlation_id=correlation_id,
            user_id=user_id,
            command=command
        )
        return True, None, None


def create_or_update_user(
    user_id: str,
    username: str,
    correlation_id: Optional[str] = None,
    **kwargs
) -> bool:
    """Create or update user in user-manager.

    Args:
        user_id: Discord user ID
        username: Discord username
        correlation_id: Correlation ID for logging
        **kwargs: Additional user data

    Returns:
        True if successful, False otherwise
    """
    if not USER_MANAGER_URL:
        return False

    try:
        auth_token = get_auth_token()
        headers = {}
        if correlation_id:
            headers['X-Correlation-ID'] = correlation_id
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'

        response = requests.post(
            f"{USER_MANAGER_URL}/api/users",
            json={
                'user_id': user_id,
                'username': username,
                **kwargs
            },
            headers=headers,
            timeout=2
        )

        if response.status_code == 200:
            logger.debug(
                "User created/updated",
                correlation_id=correlation_id,
                user_id=user_id,
                username=username
            )
            return True
        else:
            logger.warning(
                "Failed to create/update user",
                correlation_id=correlation_id,
                user_id=user_id,
                status_code=response.status_code
            )
            return False

    except Exception as e:
        logger.error(
            "Error creating/updating user",
            error=e,
            correlation_id=correlation_id,
            user_id=user_id
        )
        return False


def increment_user_usage(
    user_id: str,
    command: str,
    correlation_id: Optional[str] = None
) -> bool:
    """Increment user usage counter.

    Args:
        user_id: Discord user ID
        command: Command name
        correlation_id: Correlation ID for logging

    Returns:
        True if successful, False otherwise
    """
    if not USER_MANAGER_URL:
        return False

    try:
        auth_token = get_auth_token()
        headers = {}
        if correlation_id:
            headers['X-Correlation-ID'] = correlation_id
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'

        response = requests.post(
            f"{USER_MANAGER_URL}/api/users/{user_id}/increment",
            json={'command': command},
            headers=headers,
            timeout=2
        )

        if response.status_code == 200:
            logger.debug(
                "User usage incremented",
                correlation_id=correlation_id,
                user_id=user_id,
                command=command
            )
            return True
        else:
            logger.warning(
                "Failed to increment user usage",
                correlation_id=correlation_id,
                user_id=user_id,
                status_code=response.status_code
            )
            return False

    except Exception as e:
        logger.error(
            "Error incrementing user usage",
            error=e,
            correlation_id=correlation_id,
            user_id=user_id
        )
        return False


def get_rate_limit_error_response(
    rate_limit_info: Dict,
    interaction_type: str = 'discord'
) -> Tuple[Dict, int]:
    """Get error response for rate limit exceeded.

    Args:
        rate_limit_info: Rate limit information from user-manager
        interaction_type: 'discord' or 'web'

    Returns:
        Tuple of (response_dict, status_code)
    """
    remaining = rate_limit_info.get('remaining', 0)
    reset_in = rate_limit_info.get('reset_in', 0)
    max_calls = rate_limit_info.get('max', 0)

    if interaction_type == 'discord':
        return {
            'type': 4,
            'data': {
                'content': f"⏱️ Rate limit exceeded! You've used {max_calls - remaining}/{max_calls} calls. Try again in {reset_in} seconds.",
                'flags': 64  # Ephemeral
            }
        }, 200
    else:
        return {
            'status': 'error',
            'message': f"Rate limit exceeded. Try again in {reset_in} seconds.",
            'rate_limit': {
                'remaining': remaining,
                'reset_in': reset_in,
                'max': max_calls
            }
        }, 429

