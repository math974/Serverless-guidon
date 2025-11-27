"""Snapshot command handler."""
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from command_registry import CommandHandler
from shared.observability import init_observability
from shared.embed_utils import (
    create_error_embed,
    create_warning_embed,
    create_embed,
    create_response,
    extract_user_info,
    create_user_author,
    create_user_thumbnail,
    COLOR_SNAPSHOT,
    rate_limit_embed,
)
from shared.canvas_client import CanvasClient
from shared.user_client import UserManagementClient

logger, _ = init_observability('processor-snapshot-handler', app=None)

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

@CommandHandler.register('snapshot')
def handle_snapshot(interaction: dict = None):
    correlation_id = interaction.get('correlation_id') if interaction else None

    canvas_client = get_canvas_client()
    if not canvas_client.base_url:
        return create_error_embed("Service unavailable", "Canvas service is not configured.")

    user_id, username, avatar_url = extract_user_info(interaction)
    if not user_id:
        return create_error_embed("Unknown user", "Unable to resolve your Discord identity.")

    user_client = get_user_client()
    if not user_client:
        return create_error_embed("Service unavailable", "User service is unavailable. Please try again.")

    try:
        rate_limit = user_client.check_rate_limit(user_id, username, 'snapshot', correlation_id=correlation_id)
        if not rate_limit.get('allowed', True):
            return rate_limit_embed(rate_limit, 'snapshot')
    except Exception as exc:
        logger.warning("Snapshot rate-limit check failed, allowing command", error=exc, correlation_id=correlation_id, user_id=user_id)

    result = canvas_client.create_snapshot(user_id, username, correlation_id)
    if not result.get('success'):
        return create_error_embed("Snapshot failed", result.get('error', 'Could not generate the snapshot.'))

    try:
        user_client.increment_usage(user_id, 'snapshot', correlation_id=correlation_id)
    except Exception as exc:
        logger.warning("Failed to increment snapshot usage", error=exc, correlation_id=correlation_id, user_id=user_id)

    snapshot_url = result.get('public_url')
    fields = [{
        'name': 'Image Details',
        'value': f'**Size:** {result.get("image_size", 480)}×{result.get("image_size", 480)} px\n**Total Pixels:** {result.get("pixel_count", 2304)}',
        'inline': False
    }]

    if snapshot_url and snapshot_url.startswith('http'):
        fields.append({
            'name': 'Download',
            'value': f'[Open full-size image in browser]({snapshot_url})',
            'inline': False
        })

    image = {'url': snapshot_url} if snapshot_url and (snapshot_url.startswith('http://') or snapshot_url.startswith('https://')) else None

    embed = create_embed(
        title='Canvas Snapshot Created',
        description=f'Snapshot successfully captured by **{username}**',
        color=COLOR_SNAPSHOT,
        fields=fields,
        footer={'text': 'Use /snapshot anytime to save the current canvas state'},
        thumbnail=create_user_thumbnail(avatar_url) if avatar_url else None,
        image=image,
        author=create_user_author(username, avatar_url) if avatar_url else None
    )
    return create_response(embed)

