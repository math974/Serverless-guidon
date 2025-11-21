"""Admin Discord commands (ban, unban, premium, etc.)."""
import os
import requests
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from command_registry import CommandHandler  # noqa: E402
from shared.observability import init_observability  # noqa: E402

USER_MANAGER_URL = os.environ.get('USER_MANAGER_URL', '')

logger, _ = init_observability('discord-processor-base-handlers', app=None)


def get_user_id_from_interaction(interaction_data: dict) -> str:
    """Extract user ID from Discord interaction."""
    member = interaction_data.get('member')
    user = (member.get('user') if member else None) or interaction_data.get('user')
    return user.get('id') if user else None


def is_admin(interaction_data: dict) -> bool:
    """Check if the user executing the command is an admin.

    Checks for:
    - Administrator permission in the guild
    - Manage Guild permission
    - Bot owner (if configured)
    """
    member = interaction_data.get('member')
    if not member:
        return False

    permissions = member.get('permissions')
    if permissions:
        if isinstance(permissions, str):
            try:
                permissions = int(permissions)
            except (ValueError, TypeError):
                return False

        # Administrator permission (0x8) or Manage Guild (0x20)
        if (permissions & 0x8) or (permissions & 0x20):
            return True
    return False


def get_auth_token():
    """Get Google Cloud identity token for calling user-manager."""
    try:
        if not USER_MANAGER_URL:
            logger.error("USER_MANAGER_URL not configured for identity token")
            return None
        from google.oauth2 import id_token
        from google.auth.transport import requests

        request_session = requests.Request()
        target_audience = USER_MANAGER_URL

        identity_token = id_token.fetch_id_token(request_session, target_audience)
        return identity_token
    except Exception as e:
        logger.error("Failed to get identity token", error=e)
    return None


def call_user_manager(endpoint: str, method: str = 'GET', data: dict = None, correlation_id: str = None) -> dict:
    """Call user-manager service."""
    if not USER_MANAGER_URL:
        logger.error("USER_MANAGER_URL not configured", correlation_id=correlation_id)
        return None

    url = f"{USER_MANAGER_URL}{endpoint}"
    headers = {'Content-Type': 'application/json'}
    if correlation_id:
        headers['X-Correlation-ID'] = correlation_id

    # Add authentication token
    auth_token = get_auth_token()
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=5)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=5)
        elif method == 'PUT':
            response = requests.put(url, json=data, headers=headers, timeout=5)
        else:
            return None

        if response.status_code == 200:
            return response.json()
        else:
            error_text = response.text[:200] if hasattr(response, 'text') else str(response.content[:200])
            logger.error(
                "user-manager returned error",
                correlation_id=correlation_id,
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                error_text=error_text
            )
            # Try to parse error response
            try:
                error_data = response.json()
                return {'error': error_data.get('error', 'Unknown error'), 'status_code': response.status_code}
            except:
                return {'error': f'HTTP {response.status_code}: {error_text}', 'status_code': response.status_code}
    except Exception as e:
        logger.error(
            "Exception calling user-manager",
            error=e,
            correlation_id=correlation_id,
            endpoint=endpoint,
            method=method
        )
        return None


def check_admin_and_get_target(interaction_data: dict):
    """Check if user is admin and extract target user ID and username from options."""
    if not is_admin(interaction_data):
        return False, None, None, {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Permission Denied',
                    'description': 'You need administrator permissions to use this command.',
                    'color': 0xFF0000,
                    'flags': 64  # Ephemeral
                }]
            }
        }

    # Extract target user from options
    options = interaction_data.get('data', {}).get('options', [])
    target_user_id = None
    target_username = None

    for option in options:
        if option.get('name') == 'user':
            value = option.get('value')
            if value:
                target_user_id = str(value)
                break

    resolved = interaction_data.get('data', {}).get('resolved', {})
    users = resolved.get('users', {})

    if target_user_id and target_user_id in users:
        target_user_data = users[target_user_id]
        username = target_user_data.get('username', 'unknown')
        discriminator = target_user_data.get('discriminator', '0')
        target_username = f"{username}#{discriminator}" if discriminator != '0' else username
    elif users:
        target_user_id = str(list(users.keys())[0])
        target_user_data = users[target_user_id]
        username = target_user_data.get('username', 'unknown')
        discriminator = target_user_data.get('discriminator', '0')
        target_username = f"{username}#{discriminator}" if discriminator != '0' else username

    if target_user_id and not target_username:
        user_data = call_user_manager(f'/api/users/{target_user_id}', correlation_id=interaction_data.get('correlation_id'))
        if user_data and not user_data.get('error'):
            target_username = user_data.get('username', 'Unknown User')

    return True, target_user_id, target_username, None


@CommandHandler.register('ban')
def handle_ban(interaction_data: dict):
    """Handle ban command - ban a user."""
    try:
        is_admin_user, target_user_id, target_username, error_response = check_admin_and_get_target(interaction_data)
        if not is_admin_user:
            return error_response

        if not target_user_id:
            logger.warning(
                "No target user ID found in options",
                correlation_id=correlation_id,
                interaction_data=interaction_data.get('data', {})
            )
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Error',
                        'description': 'Please specify a user to ban.',
                        'color': 0xFF0000,
                        'flags': 64
                    }]
                }
            }

        correlation_id = interaction_data.get('correlation_id', 'unknown')

        # Extract reason from options
        options = interaction_data.get('data', {}).get('options', [])
        reason = None
        for option in options:
            if option.get('name') == 'reason':
                reason = option.get('value')
                break

        result = call_user_manager(
            f'/api/users/{target_user_id}/ban',
            method='POST',
            data={'reason': reason} if reason else {},
            correlation_id=correlation_id
        )

        if result and result.get('status') == 'banned':
            user_display = target_username or "the user"
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'User Banned',
                        'description': f'{user_display} has been banned.',
                        'color': 0xFF0000,
                        'fields': [{'name': 'Reason', 'value': reason or 'No reason provided', 'inline': False}] if reason else []
                    }]
                }
            }
        else:
            logger.warning(
                "Ban failed",
                correlation_id=correlation_id,
                target_user_id=target_user_id,
                result=result
            )
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Error',
                        'description': f'Failed to ban user. {result.get("error", "Unknown error") if result else "No response from service"}',
                        'color': 0xFF0000,
                        'flags': 64
                    }]
                }
            }
    except Exception as e:
        logger.error(
            "Error in handle_ban",
            error=e,
            correlation_id=interaction_data.get('correlation_id', 'unknown')
        )
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Error',
                    'description': f'An error occurred: {str(e)}',
                    'color': 0xFF0000,
                    'flags': 64
                }]
            }
        }


@CommandHandler.register('unban')
def handle_unban(interaction_data: dict):
    """Handle unban command - unban a user."""
    try:
        is_admin_user, target_user_id, target_username, error_response = check_admin_and_get_target(interaction_data)
        if not is_admin_user:
            return error_response

        if not target_user_id:
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Error',
                        'description': 'Please specify a user to unban.',
                        'color': 0xFF0000,
                        'flags': 64
                    }]
                }
            }

        correlation_id = interaction_data.get('correlation_id', 'unknown')

        result = call_user_manager(
            f'/api/users/{target_user_id}/unban',
            method='POST',
            correlation_id=correlation_id
        )

        if result and result.get('status') == 'unbanned':
            user_display = target_username or "the user"
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'User Unbanned',
                        'description': f'{user_display} has been unbanned.',
                        'color': 0x00FF00
                    }]
                }
            }
        else:
            logger.warning(
                "Unban failed",
                correlation_id=correlation_id,
                target_user_id=target_user_id,
                result=result
            )
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Error',
                        'description': f'Failed to unban user. {result.get("error", "Unknown error") if result else "No response from service"}',
                        'color': 0xFF0000,
                        'flags': 64
                    }]
                }
            }
    except Exception as e:
        logger.error(
            "Error in handle_unban",
            error=e,
            correlation_id=interaction_data.get('correlation_id', 'unknown')
        )
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Error',
                    'description': f'An error occurred: {str(e)}',
                    'color': 0xFF0000,
                    'flags': 64
                }]
            }
        }


@CommandHandler.register('setpremium')
def handle_setpremium(interaction_data: dict):
    """Handle setpremium command - set premium status for a user."""
    try:
        is_admin_user, target_user_id, target_username, error_response = check_admin_and_get_target(interaction_data)
        if not is_admin_user:
            return error_response

        if not target_user_id:
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Error',
                        'description': 'Please specify a user.',
                        'color': 0xFF0000,
                        'flags': 64
                    }]
                }
            }

        # Extract premium status from options
        options = interaction_data.get('data', {}).get('options', [])
        is_premium = False
        for option in options:
            if option.get('name') == 'premium':
                is_premium = option.get('value', False)
                break

        correlation_id = interaction_data.get('correlation_id', 'unknown')

        result = call_user_manager(
            f'/api/users/{target_user_id}/premium',
            method='PUT',
            data={'is_premium': is_premium},
            correlation_id=correlation_id
        )

        if result and result.get('status') == 'updated':
            status_text = 'enabled' if is_premium else 'disabled'
            user_display = target_username or "the user"
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Premium Status Updated',
                        'description': f'Premium status for {user_display} has been {status_text}.',
                        'color': 0xFFD700 if is_premium else 0x808080
                    }]
                }
            }
        else:
            logger.warning(
                "Setpremium failed",
                correlation_id=correlation_id,
                target_user_id=target_user_id,
                is_premium=is_premium,
                result=result
            )
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Error',
                        'description': f'Failed to update premium status. {result.get("error", "Unknown error") if result else "No response from service"}',
                        'color': 0xFF0000,
                        'flags': 64
                    }]
                }
            }
    except Exception as e:
        logger.error(
            "Error in handle_setpremium",
            error=e,
            correlation_id=interaction_data.get('correlation_id', 'unknown')
        )
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Error',
                    'description': f'An error occurred: {str(e)}',
                    'color': 0xFF0000,
                    'flags': 64
                }]
            }
        }

