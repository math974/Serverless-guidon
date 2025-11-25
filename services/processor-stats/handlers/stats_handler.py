"""Stats command handler."""
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from command_registry import CommandHandler
from shared.observability import init_observability
from shared.embed_utils import (
    create_error_embed,
    create_embed,
    create_response,
    extract_user_info,
    create_user_author,
    create_user_thumbnail,
    COLOR_PREMIUM,
    COLOR_INFO,
)
from shared.canvas_client import CanvasClient
from shared.user_client import UserManagementClient

logger, _ = init_observability('processor-stats-handler', app=None)

_canvas_client = None
_user_client = None

def get_canvas_client():
    global _canvas_client
    if _canvas_client is None:
        _canvas_client = CanvasClient()
    return _canvas_client

def get_user_client() -> Optional[UserManagementClient]:
    global _user_client
    if _user_client is None:
        try:
            _user_client = UserManagementClient()
        except Exception as exc:
            logger.error("Cannot instantiate UserManagementClient", error=exc)
            return None
    return _user_client

@CommandHandler.register('stats')
def handle_stats(interaction: dict = None):
    correlation_id = interaction.get('correlation_id') if interaction else None
    user_id, username, avatar_url = extract_user_info(interaction)

    if not user_id:
        return create_error_embed("Unavailable", "Unable to retrieve statistics right now.")

    canvas_client = get_canvas_client()
    user_client = get_user_client()

    if not user_client:
        return create_error_embed("Service unavailable", "User service is unavailable. Please try again.")

    try:
        user_stats = user_client.get_user_stats(user_id, correlation_id=correlation_id)
        canvas_stats = canvas_client.get_canvas_stats(correlation_id) if canvas_client.base_url else {}
        draw_limits = user_client.get_rate_limit_info(user_id, 'draw', correlation_id=correlation_id)
    except Exception as exc:
        logger.error("Failed to fetch stats", error=exc, correlation_id=correlation_id, user_id=user_id)
        return create_error_embed("Error", "Could not load statistics.")

    is_premium = user_stats.get('is_premium', False) if user_stats else False
    tier_label = 'Premium' if is_premium else 'Standard'

    fields = []
    fields.append({
        'name': 'Your Account',
        'value': f'**Tier:** {tier_label}\n**Your Pixels:** {user_stats.get("total_draws", 0) if user_stats else 0}',
        'inline': False
    })
    fields.append({
        'name': 'Rate Limits',
        'value': f'**Draws remaining:** {draw_limits.get("remaining", 0)}/{draw_limits.get("max", 0)}',
        'inline': False
    })
    fields.append({
        'name': 'Canvas Statistics',
        'value': f'**Total pixels:** {canvas_stats.get("total_pixels", 0)}\n**Contributors:** {canvas_stats.get("unique_contributors", 0)}',
        'inline': False
    })

    embed = create_embed(
        title='Statistics Dashboard',
        description=f'Detailed statistics for **{username}**',
        color=COLOR_PREMIUM if is_premium else COLOR_INFO,
        fields=fields,
        footer={'text': 'Use /draw and /snapshot to climb the leaderboard • /leaderboard to see top artists'},
        thumbnail=create_user_thumbnail(avatar_url) if avatar_url else None,
        author=create_user_author(username, avatar_url) if avatar_url else None
    )
    return create_response(embed, ephemeral=True)

