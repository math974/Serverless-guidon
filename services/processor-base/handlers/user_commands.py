"""User management Discord commands."""
import os
import requests
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from command_registry import CommandHandler  # noqa: E402
from shared.observability import init_observability  # noqa: E402
from shared.processor_utils import get_authenticated_headers  # noqa: E402
from shared.embed_utils import (  # noqa: E402
    create_error_embed,
    create_info_embed,
    create_success_embed,
    create_embed,
    create_response,
    get_user_avatar_url,
    extract_user_info,
    create_user_author,
    create_user_thumbnail,
    COLOR_INFO,
    COLOR_PREMIUM,
    COLOR_SUCCESS,
    COLOR_ERROR
)

USER_MANAGER_URL = os.environ.get('USER_MANAGER_URL', '')

logger, _ = init_observability('discord-processor-base-handlers', app=None)


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
    headers = get_authenticated_headers(USER_MANAGER_URL, correlation_id, logger)
    headers['Content-Type'] = 'application/json'

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
        return create_error_embed(
            'Service Unavailable',
            'User management service is not available.'
        )
    if user_id:
        member = interaction_data.get('member')
        user = (member.get('user') if member else None) or interaction_data.get('user')
        if user:
            username = user.get('username', 'unknown')
            discriminator = user.get('discriminator', '0')
            full_username = f"{username}#{discriminator}" if discriminator != '0' else username
            existing_user = call_user_manager(f'/api/users/{user_id}', correlation_id=correlation_id)
            if not existing_user:
                call_user_manager(
                    '/api/users',
                    method='POST',
                    data={
                        'user_id': user_id,
                        'username': full_username,
                        'avatar': user.get('avatar'),
                        'discriminator': discriminator
                    },
                    correlation_id=correlation_id
                )

    # - User stats -
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

    return create_info_embed(
        title='Statistics',
        description='User and global statistics',
        fields=fields,
        footer={'text': 'User Management'}
    )


@CommandHandler.register('leaderboard')
def handle_leaderboard(interaction_data: dict):
    """Handle leaderboard command - show top users."""
    correlation_id = interaction_data.get('correlation_id', 'unknown')

    if not USER_MANAGER_URL:
        from shared.embed_utils import create_error_embed
        return create_error_embed(
            'Service Unavailable',
            'User management service is not available.'
        )

    leaderboard_data = call_user_manager('/api/stats/leaderboard?limit=10', correlation_id=correlation_id) or {}
    leaderboard = leaderboard_data.get('leaderboard', [])

    if not leaderboard:
        from shared.embed_utils import create_info_embed
        return create_info_embed(
            title='Leaderboard',
            description='No users found yet. Be the first to draw!'
        )

    from shared.embed_utils import (
        create_embed,
        create_response,
        get_user_avatar_url,
        create_user_author,
        COLOR_PREMIUM
    )

    fields = []
    champion_thumbnail = None
    author = None
    medals = ['🥇', '🥈', '🥉']

    # Top 3 with their information
    for i, user in enumerate(leaderboard[:3]):
        username = user.get('username', 'Unknown')
        total_draws = user.get('total_draws', 0)
        is_premium = user.get('is_premium', False)
        medal = medals[i]
        premium_badge = ' ⭐ Premium' if is_premium else ''
        avatar_url = None
        user_id = user.get('user_id')
        if user_id:
            avatar_url = get_user_avatar_url(
                user_id,
                user.get('avatar'),
                user.get('discriminator', '0')
            )
        if i == 0 and avatar_url:
            champion_thumbnail = create_user_thumbnail(avatar_url)
            author = create_user_author(username, avatar_url)
        mention_display = f"<@{user_id}>" if user_id else f"**{username}**"

        rank_name = ['Champion', 'Runner-up', 'Third Place'][i]

        fields.append({
            'name': f'{medal} {rank_name}',
            'value': f'{mention_display}\n**{total_draws}** pixels drawn{premium_badge}',
            'inline': True
        })

    if len(leaderboard) > 3:
        others = []
        for i, user in enumerate(leaderboard[3:10], start=4):
            username = user.get('username', 'Unknown')
            total_draws = user.get('total_draws', 0)
            is_premium = user.get('is_premium', False)
            premium_badge = ' ⭐' if is_premium else ''
            user_id = user.get('user_id')
            mention_display = f"<@{user_id}>" if user_id else username

            others.append(f"**{i}.** {mention_display}{premium_badge} - **{total_draws}** pixels")

        if others:
            fields.append({
                'name': 'Rankings 4-10',
                'value': '\n'.join(others),
                'inline': False
            })

    embed = create_embed(
        title='Leaderboard',
        description='Top artists by total pixels drawn',
        color=COLOR_PREMIUM,
        fields=fields,
        footer={'text': 'Top 10 users by draws • Use /draw to climb the leaderboard!'},
        thumbnail=champion_thumbnail,
        author=author
    )

    return create_response(embed)

@CommandHandler.register('register')
def handle_register(interaction_data: dict):
    """Handle register command - register user in the system."""
    user_id = get_user_id_from_interaction(interaction_data)
    correlation_id = interaction_data.get('correlation_id', 'unknown')

    if not USER_MANAGER_URL:
        return create_error_embed(
            'Service Unavailable',
            'User management service is not available.'
        )

    if not user_id:
        return create_error_embed(
            'User Identification Failed',
            'Could not identify user.'
        )

    member = interaction_data.get('member')
    user = (member.get('user') if member else None) or interaction_data.get('user')
    if not user:
        return create_error_embed(
            'User Information Missing',
            'Could not get user information.'
        )

    username = user.get('username', 'unknown')
    discriminator = user.get('discriminator', '0')
    full_username = f"{username}#{discriminator}" if discriminator != '0' else username

    existing_user = call_user_manager(f'/api/users/{user_id}', correlation_id=correlation_id)

    if existing_user and not existing_user.get('error'):
        return create_success_embed(
            title='Already Registered',
            description=f'Your account is already registered!\n\n**Username:** {existing_user.get("username", full_username)}',
            footer={'text': 'User Management'},
            ephemeral=True
        )

    # Create user
    result = call_user_manager(
        '/api/users',
        method='POST',
        data={
            'user_id': user_id,
            'username': full_username,
            'avatar': user.get('avatar'),
            'discriminator': discriminator
        },
        correlation_id=correlation_id
    )

    if result and not result.get('error'):
        return create_success_embed(
            title='Registration Successful',
            description=f'Your account has been registered successfully!\n\n**Username:** {full_username}',
            footer={'text': 'User Management'},
            ephemeral=True
        )
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

        return create_error_embed(
            'Error',
            error_msg,
            ephemeral=True
        )


@CommandHandler.register('userinfo')
def handle_userinfo(interaction_data: dict):
    """Handle userinfo command - show user information."""
    correlation_id = interaction_data.get('correlation_id', 'unknown')

    if not USER_MANAGER_URL:
        return create_error_embed(
            'Service Unavailable',
            'User management service is not available.'
        )

    target_user_id = None
    target_username = None

    data = interaction_data.get('data', {})
    options = data.get('options', [])
    for option in options:
        if option.get('name') == 'user':
            value = option.get('value')
            if value:
                target_user_id = str(value)
                break

    resolved = data.get('resolved', {})
    users = resolved.get('users', {})
    if target_user_id and target_user_id in users:
        target_user_data = users[target_user_id]
        username = target_user_data.get('username', 'unknown')
        discriminator = target_user_data.get('discriminator', '0')
        target_username = f"{username}#{discriminator}" if discriminator != '0' else username

    if not target_user_id:
        target_user_id = get_user_id_from_interaction(interaction_data)
        if not target_user_id:
            return create_error_embed(
                'User Identification Failed',
                'Could not identify user.'
            )
        member = interaction_data.get('member')
        user = (member.get('user') if member else None) or interaction_data.get('user')
        if user:
            username = user.get('username', 'unknown')
            discriminator = user.get('discriminator', '0')
            target_username = f"{username}#{discriminator}" if discriminator != '0' else username

            existing_user = call_user_manager(f'/api/users/{target_user_id}', correlation_id=correlation_id)
            if not existing_user or existing_user.get('error'):
                call_user_manager(
                    '/api/users',
                    method='POST',
                    data={
                        'user_id': target_user_id,
                        'username': target_username,
                        'avatar': user.get('avatar'),
                        'discriminator': discriminator
                    },
                    correlation_id=correlation_id
                )

    if not target_user_id:
        logger.error(
            "target_user_id is None after all checks",
            correlation_id=correlation_id,
            interaction_data_keys=list(interaction_data.keys()) if interaction_data else []
        )
        return create_error_embed(
            'User Identification Failed',
            'Could not identify user. Please specify a user or ensure you are authenticated.'
        )

    user = call_user_manager(f'/api/users/{target_user_id}', correlation_id=correlation_id)

    if not user or user.get('error'):
        error_msg = 'User information not found.'
        if user and user.get('error'):
            error_msg = f"Error: {user.get('error', 'Unknown error')}"
        return create_error_embed(
            'User Not Found',
            error_msg
        )

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

    if rate_limit_info and not rate_limit_info.get('error') and rate_limit_info.get('remaining') is not None:
        fields.append({
            'name': 'Rate Limit',
            'value': f"**Remaining:** {rate_limit_info.get('remaining', 0)}/{rate_limit_info.get('max', 0)}\n**Reset in:** {rate_limit_info.get('reset_in', 0)}s",
            'inline': True
        })

    user_id = user.get('user_id') or target_user_id
    thumbnail = None
    if user_id:
        try:
            avatar_hash = None
            discriminator = '0'

            member = interaction_data.get('member')
            interaction_user = (member.get('user') if member else None) or interaction_data.get('user')
            if interaction_user and str(interaction_user.get('id')) == str(user_id):
                avatar_hash = interaction_user.get('avatar')
                discriminator = interaction_user.get('discriminator', '0')
            else:
                resolved = interaction_data.get('data', {}).get('resolved', {})
                users = resolved.get('users', {})
                if str(user_id) in users:
                    user_data = users[str(user_id)]
                    avatar_hash = user_data.get('avatar')
                    discriminator = user_data.get('discriminator', '0')

            avatar_url = get_user_avatar_url(str(user_id), avatar_hash, discriminator)
            if avatar_url:
                thumbnail = create_user_thumbnail(avatar_url)
        except Exception as e:
            logger.warning(
                "Failed to get user avatar",
                error=e,
                correlation_id=correlation_id,
                user_id=user_id
            )

    display_username = target_username or user.get('username', 'Unknown')
    if not display_username or display_username == 'Unknown':
        display_username = f"User {target_user_id}" if target_user_id else 'Unknown User'

    embed_color = COLOR_INFO if not user.get('is_banned') else COLOR_ERROR
    embed = create_embed(
        title=f"User Info: {display_username}",
        description='User information',
        color=embed_color,
        fields=fields,
        footer={'text': 'User Management'},
        thumbnail=thumbnail
    )
    return create_response(embed)

