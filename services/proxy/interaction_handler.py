"""Interaction processing logic."""
import os
from command_handler import handle_simple_command
from response_utils import get_proxy_url
from user_integration import (
    get_user_id_from_interaction,
    check_user_allowed,
    get_rate_limit_error_response,
    is_user_registered
)
from shared.observability import init_observability

logger, _ = init_observability('discord-proxy', app=None)

# - Commands that don't require registration -
NO_REGISTRATION_REQUIRED = {'register', 'help', 'ping', 'hello'}


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

    user_payload = None
    if interaction_type == 'discord':
        member = interaction_data.get('member', {})
        user = member.get('user') or interaction_data.get('user', {})
        if user:
            username = user.get('username', 'unknown')
            discriminator = user.get('discriminator', '0')
            full_username = f"{username}#{discriminator}" if discriminator != '0' else username
            user_payload = {
                'username': full_username,
                'avatar': user.get('avatar')
            }
    else:  # web interaction
        user_id_from_data = interaction_data.get('user_id') or interaction_data.get('user', {}).get('id')
        if user_id_from_data:
            user_data = interaction_data.get('user', {})
            username = user_data.get('username') or interaction_data.get('username', 'web-user')
            user_payload = {
                'username': username,
                'avatar': user_data.get('avatar') or interaction_data.get('avatar')
            }

    user_id = get_user_id_from_interaction(interaction_data)

    if user_id and command_name not in NO_REGISTRATION_REQUIRED:
        if not is_user_registered(user_id, correlation_id=correlation_id):
            if interaction_type == 'discord':
                from shared.embed_utils import create_error_embed
                return create_error_embed(
                    'Registration Required',
                    f'You must register your account before using commands.\n\nUse `/register` to create your account.',
                    ephemeral=True
                ), 200
            else:
                return {
                    'status': 'error',
                    'message': 'You must register your account before using commands. Use /register to create your account.'
                }, 403

    art_commands = {'draw', 'snapshot'}
    enforce_limits = command_name in art_commands
    if user_id and enforce_limits:
        allowed, rate_limit_info, error_message = check_user_allowed(
            user_id,
            command_name,
            correlation_id=correlation_id,
            user_payload=user_payload
        )

        if not allowed:
            if rate_limit_info:
                return get_rate_limit_error_response(rate_limit_info, interaction_type)
            else:
                if interaction_type == 'discord':
                    return {
                        'type': 4,
                        'data': {
                            'content': f"❌ {error_message or 'Access denied'}",
                            'flags': 64
                        }
                    }, 200
                else:
                    return {
                        'status': 'error',
                        'message': error_message or 'Access denied'
                    }, 403

    # - Handle simple commands -
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
        user_id = interaction_data.get('user_id') or interaction_data.get('user', {}).get('id')
        user_data = interaction_data.get('user', {})

        interaction_obj = {
            'type': 2,
            'data': {
                'name': interaction_data.get('command'),
                'options': interaction_data.get('options', [])
            },
            'token': interaction_data.get('token', 'web-interaction'),
            'application_id': interaction_data.get('application_id', 'web-client')
        }

        if user_id:
            interaction_obj['user'] = {
                'id': user_id,
                'username': user_data.get('username') or interaction_data.get('username', 'web-user'),
                'discriminator': user_data.get('discriminator', '0'),
                'avatar': user_data.get('avatar') or interaction_data.get('avatar')
            }

        webhook_url = interaction_data.get('webhook_url')
        if not webhook_url:
            logger.warning(
                "Web interaction missing webhook_url - frontend must provide webhook URL for responses"
            )
            return None

        return {
            'interaction': interaction_obj,
            'interaction_type': 'web',
            'webhook_url': webhook_url,
            'token': interaction_data.get('token')  # Include token at root level for easy access
        }
    else:
        result = {
            'interaction': interaction_data,
            'discord_bot_token': os.environ.get('DISCORD_BOT_TOKEN')
        }
        if signature and timestamp:
            result['headers'] = {
                'signature': signature,
                'timestamp': timestamp
            }
        return result
