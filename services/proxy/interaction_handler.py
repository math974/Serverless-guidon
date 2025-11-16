"""Interaction processing logic."""
from command_handler import handle_simple_command
from response_utils import get_proxy_url
from user_integration import (
    get_user_id_from_interaction,
    check_user_allowed,
    create_or_update_user,
    get_rate_limit_error_response
)
from shared.observability import init_observability

logger, _ = init_observability('discord-proxy', app=None)


def process_interaction(
    interaction_data: dict,
    interaction_type: str = 'discord',
    correlation_id: str = None
) -> tuple:
    """Process an interaction (Discord or Web).

    Args:
        interaction_data: Parsed interaction data
        interaction_type: 'discord' or 'web'
        correlation_id: Correlation ID for logging

    Returns:
        Tuple of (response_dict, status_code) or None if needs Pub/Sub
    """
    if interaction_type == 'discord' and interaction_data.get('type') == 1:
        return {'type': 1}, 200

    if interaction_type == 'discord':
        if interaction_data.get('type') != 2:
            return None
        command_name = interaction_data.get('data', {}).get('name')
    else:
        command_name = interaction_data.get('command')

    if not command_name:
        return None

    # Check user permissions and rate limits
    user_id = get_user_id_from_interaction(interaction_data)
    if user_id:
        # Check if user is allowed (not banned, rate limit OK)
        allowed, rate_limit_info, error_message = check_user_allowed(
            user_id,
            command_name,
            correlation_id=correlation_id
        )

        if not allowed:
            if rate_limit_info:
                # Rate limit exceeded
                return get_rate_limit_error_response(rate_limit_info, interaction_type)
            else:
                # User is banned or other error
                if interaction_type == 'discord':
                    return {
                        'type': 4,
                        'data': {
                            'content': f"❌ {error_message or 'Access denied'}",
                            'flags': 64  # Ephemeral
                        }
                    }, 200
                else:
                    return {
                        'status': 'error',
                        'message': error_message or 'Access denied'
                    }, 403

        # Create/update user if needed (async, don't block)
        if interaction_type == 'discord':
            member = interaction_data.get('member', {})
            user = member.get('user') or interaction_data.get('user', {})
            username = user.get('username', 'unknown')
            discriminator = user.get('discriminator', '0')
            full_username = f"{username}#{discriminator}" if discriminator != '0' else username

            # Try to create/update user (non-blocking)
            try:
                create_or_update_user(
                    user_id,
                    full_username,
                    correlation_id=correlation_id,
                    avatar=user.get('avatar')
                )
            except Exception as e:
                logger.warning(
                    "Failed to create/update user (non-blocking)",
                    error=e,
                    correlation_id=correlation_id,
                    user_id=user_id
                )

    simple_response = handle_simple_command(command_name, interaction_type)
    if simple_response:
        return simple_response, 200

    return None


def prepare_pubsub_data(interaction_data: dict, interaction_type: str,
                        signature: str = None, timestamp: str = None,
                        request=None) -> dict:
    """Prepare data for Pub/Sub publication.

    Args:
        interaction_data: Original interaction data
        interaction_type: 'discord' or 'web'
        signature: Discord signature (optional)
        timestamp: Discord timestamp (optional)
        request: Functions Framework request object (optional)

    Returns:
        Dictionary ready for Pub/Sub
    """
    proxy_url = get_proxy_url(request)

    if interaction_type == 'web':
        return {
            'interaction': {
                'type': 2,
                'data': {
                    'name': interaction_data.get('command'),
                    'options': interaction_data.get('options', [])
                },
                'token': interaction_data.get('token', 'web-interaction'),
                'application_id': interaction_data.get('application_id', 'web-client')
            },
            'interaction_type': 'web',
            'proxy_url': proxy_url
        }
    else:
        result = {
            'interaction': interaction_data,
            'proxy_url': proxy_url
        }
        if signature and timestamp:
            result['headers'] = {
                'signature': signature,
                'timestamp': timestamp
            }
        return result
