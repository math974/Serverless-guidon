"""User management Discord commands."""
import os
import requests
from datetime import datetime, timezone
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from command_registry import CommandHandler  # noqa: E402
from shared.observability import init_observability  # noqa: E402

USER_MANAGER_URL = os.environ.get('USER_MANAGER_URL', '')

logger, _ = init_observability('discord-processor-base-handlers', app=None)


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


def get_user_id_from_interaction(interaction_data: dict) -> str:
    """Extract user ID from Discord interaction."""
    member = interaction_data.get('member')
    user = (member.get('user') if member else None) or interaction_data.get('user')
    return user.get('id') if user else None


def call_user_manager(endpoint: str, method: str = 'GET', data: dict = None, correlation_id: str = None) -> dict:
    """Call user-manager service."""
    if not USER_MANAGER_URL:
        logger.error("USER_MANAGER_URL not configured", correlation_id=correlation_id)
        return None

    url = f"{USER_MANAGER_URL}{endpoint}"
    headers = {'Content-Type': 'application/json'}
    if correlation_id:
        headers['X-Correlation-ID'] = correlation_id

    # Add identity token for calling user-manager
    auth_token = get_auth_token()
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=5)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=5)
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
            try:
                error_data = response.json()
                return {'error': error_data.get('error', 'Unknown error'), 'status_code': response.status_code, 'details': error_data.get('details', error_text)}
            except:
                return {'error': f'HTTP {response.status_code}', 'status_code': response.status_code, 'details': error_text}
    except Exception as e:
        logger.error(
            "Exception calling user-manager",
            error=e,
            correlation_id=correlation_id,
            endpoint=endpoint,
            method=method
        )
        return None


@CommandHandler.register('stats')
def handle_stats(interaction_data: dict):
    """Handle stats command - show user statistics."""
    user_id = get_user_id_from_interaction(interaction_data)
    correlation_id = interaction_data.get('correlation_id', 'unknown')

    if not USER_MANAGER_URL:
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Error',
                    'description': 'User management service is not available.',
                    'color': 0xFF0000
                }]
            }
        }
    if user_id:
        member = interaction_data.get('member')
        user = (member.get('user') if member else None) or interaction_data.get('user')
        if user:
            username = user.get('username', 'unknown')
            existing_user = call_user_manager(f'/api/users/{user_id}', correlation_id=correlation_id)
            if not existing_user:
                call_user_manager(
                    '/api/users',
                    method='POST',
                    data={'user_id': user_id, 'username': username},
                    correlation_id=correlation_id
                )

    # Get user stats
    user = call_user_manager(f'/api/users/{user_id}', correlation_id=correlation_id) if user_id else None
    total_users = call_user_manager('/api/stats/users', correlation_id=correlation_id) or {}
    active_users = call_user_manager('/api/stats/active?hours=24', correlation_id=correlation_id) or {}

    fields = []
    if user:
        fields.append({
            'name': 'Your Stats',
            'value': f"**Draws:** {user.get('total_draws', 0)}\n**Premium:** {'Yes' if user.get('is_premium') else 'No'}",
            'inline': True
        })

    fields.append({
        'name': 'Global Stats',
        'value': f"**Total Users:** {total_users.get('total_users', 0)}\n**Active (24h):** {active_users.get('active_users', 0)}",
        'inline': True
    })

    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': 'Statistics',
                'description': 'User and global statistics',
                'color': 0x0066CC,
                'fields': fields,
                'footer': {
                    'text': 'User Management'
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }]
        }
    }


@CommandHandler.register('leaderboard')
def handle_leaderboard(interaction_data: dict):
    """Handle leaderboard command - show top users."""
    correlation_id = interaction_data.get('correlation_id', 'unknown')

    if not USER_MANAGER_URL:
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Error',
                    'description': 'User management service is not available.',
                    'color': 0xFF0000
                }]
            }
        }

    leaderboard_data = call_user_manager('/api/stats/leaderboard?limit=10', correlation_id=correlation_id) or {}
    leaderboard = leaderboard_data.get('leaderboard', [])

    if not leaderboard:
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Leaderboard',
                    'description': 'No users found yet.',
                    'color': 0x0066CC
                }]
            }
        }

    # Format leaderboard
    leaderboard_text = []
    medals = ['🥇', '🥈', '🥉']
    for i, user in enumerate(leaderboard[:10]):
        medal = medals[i] if i < 3 else f"{i+1}."
        premium_badge = '⭐' if user.get('is_premium') else ''
        leaderboard_text.append(
            f"{medal} {premium_badge} **{user.get('username', 'Unknown')}** - {user.get('total_draws', 0)} draws"
        )

    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': '🏆 Leaderboard',
                'description': '\n'.join(leaderboard_text) if leaderboard_text else 'No users yet.',
                'color': 0xFFD700,
                'footer': {
                    'text': 'Top 10 users by draws'
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }]
        }
    }


@CommandHandler.register('register')
def handle_register(interaction_data: dict):
    """Handle register command - register user in the system."""
    user_id = get_user_id_from_interaction(interaction_data)
    correlation_id = interaction_data.get('correlation_id', 'unknown')

    if not USER_MANAGER_URL:
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Error',
                    'description': 'User management service is not available.',
                    'color': 0xFF0000,
                    'flags': 64
                }]
            }
        }

    if not user_id:
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Error',
                    'description': 'Could not identify user.',
                    'color': 0xFF0000,
                    'flags': 64
                }]
            }
        }

    # Get user info from interaction
    member = interaction_data.get('member')
    user = (member.get('user') if member else None) or interaction_data.get('user')
    if not user:
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Error',
                    'description': 'Could not get user information.',
                    'color': 0xFF0000,
                    'flags': 64
                }]
            }
        }

    username = user.get('username', 'unknown')
    discriminator = user.get('discriminator', '0')
    full_username = f"{username}#{discriminator}" if discriminator != '0' else username

    existing_user = call_user_manager(f'/api/users/{user_id}', correlation_id=correlation_id)

    if existing_user and not existing_user.get('error'):
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': '✅ Already Registered',
                    'description': f'Your account is already registered!\n\n**Username:** {existing_user.get("username", full_username)}',
                    'color': 0x00FF00,
                    'footer': {
                        'text': 'User Management'
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }]
            },
            'flags': 64
        }

    # Create user
    result = call_user_manager(
        '/api/users',
        method='POST',
        data={
            'user_id': user_id,
            'username': full_username,
            'avatar': user.get('avatar')
        },
        correlation_id=correlation_id
    )

    if result and not result.get('error'):
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': '✅ Registration Successful',
                    'description': f'Your account has been registered successfully!\n\n**Username:** {full_username}',
                    'color': 0x00FF00,
                    'footer': {
                        'text': 'User Management'
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }]
            },
            'flags': 64
        }
    else:
        # Extract error details
        error_msg = 'Failed to register account. Please try again later.'
        if result and result.get('error'):
            error_msg = f"Error: {result.get('error', 'Unknown error')}"
            if result.get('details'):
                error_msg += f"\nDetails: {result.get('details', '')[:100]}"

        logger.error(
            "Registration failed",
            correlation_id=correlation_id,
            user_id=user_id,
            username=full_username,
            error_result=result
        )

        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Error',
                    'description': error_msg,
                    'color': 0xFF0000,
                    'flags': 64
                }]
            }
        }


@CommandHandler.register('userinfo')
def handle_userinfo(interaction_data: dict):
    """Handle userinfo command - show user information."""
    correlation_id = interaction_data.get('correlation_id', 'unknown')

    if not USER_MANAGER_URL:
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'Error',
                    'description': 'User management service is not available.',
                    'color': 0xFF0000
                }]
            }
        }

    # Extract target user from options or use the command executor
    target_user_id = None
    target_username = None

    # Check if a user was specified in options
    options = interaction_data.get('data', {}).get('options', [])
    for option in options:
        if option.get('name') == 'user':
            value = option.get('value')
            if value:
                target_user_id = str(value)
                break

    # Get username from resolved users if available
    resolved = interaction_data.get('data', {}).get('resolved', {})
    users = resolved.get('users', {})
    if target_user_id and target_user_id in users:
        target_user_data = users[target_user_id]
        username = target_user_data.get('username', 'unknown')
        discriminator = target_user_data.get('discriminator', '0')
        target_username = f"{username}#{discriminator}" if discriminator != '0' else username

    # If no user specified, use the command executor
    if not target_user_id:
        target_user_id = get_user_id_from_interaction(interaction_data)
        if not target_user_id:
            return {
                'type': 4,
                'data': {
                    'embeds': [{
                        'title': 'Error',
                        'description': 'Could not identify user.',
                        'color': 0xFF0000
                    }]
                }
            }
        # Get username from interaction
        member = interaction_data.get('member')
        user = (member.get('user') if member else None) or interaction_data.get('user')
        if user:
            username = user.get('username', 'unknown')
            discriminator = user.get('discriminator', '0')
            target_username = f"{username}#{discriminator}" if discriminator != '0' else username

            # Ensure user exists (create if needed) only for self
            existing_user = call_user_manager(f'/api/users/{target_user_id}', correlation_id=correlation_id)
            if not existing_user:
                call_user_manager(
                    '/api/users',
                    method='POST',
                    data={'user_id': target_user_id, 'username': username},
                    correlation_id=correlation_id
                )

    user = call_user_manager(f'/api/users/{target_user_id}', correlation_id=correlation_id)

    if not user:
        return {
            'type': 4,
            'data': {
                'embeds': [{
                    'title': 'User Not Found',
                    'description': 'User information not found.',
                    'color': 0xFF0000
                }]
            }
        }

    # Get rate limit info
    rate_limit_info = call_user_manager(
        f'/api/rate-limit/{target_user_id}?command=draw',
        correlation_id=correlation_id
    ) or {}

    status_badges = []
    if user.get('is_premium'):
        status_badges.append('⭐ Premium')
    if user.get('is_banned'):
        status_badges.append('🚫 Banned')

    fields = [
        {
            'name': 'Usage',
            'value': f"**Draws:** {user.get('total_draws', 0)}",
            'inline': True
        },
        {
            'name': 'Status',
            'value': '\n'.join(status_badges) if status_badges else 'Normal',
            'inline': True
        }
    ]

    if rate_limit_info:
        fields.append({
            'name': 'Rate Limit',
            'value': f"**Remaining:** {rate_limit_info.get('remaining', 0)}/{rate_limit_info.get('max', 0)}\n**Reset in:** {rate_limit_info.get('reset_in', 0)}s",
            'inline': True
        })

    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': f"User Info: {target_username or user.get('username', 'Unknown')}",
                'description': f"User information",
                'color': 0x0066CC if not user.get('is_banned') else 0xFF0000,
                'fields': fields,
                'footer': {
                    'text': 'User Management'
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }]
        }
    }

