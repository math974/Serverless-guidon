"""Draw command handler."""
import re
import os
import sys
from typing import Dict, Optional, Tuple, Any

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
    CANVAS_SIZE,
    COLOR_NAMES,
    extract_options,
    rate_limit_embed,
)
from shared.canvas_client import CanvasClient
from shared.user_client import UserManagementClient

logger, _ = init_observability('processor-draw-handler', app=None)

# Global clients
_canvas_client = None
_user_client = None

def get_canvas_client():
    """Get or create CanvasClient instance."""
    global _canvas_client
    if _canvas_client is None:
        _canvas_client = CanvasClient()
    return _canvas_client

def get_user_client() -> Optional[UserManagementClient]:
    """Get or create UserManagementClient instance."""
    global _user_client
    if _user_client is None:
        try:
            _user_client = UserManagementClient()
        except Exception as exc:
            logger.error("Cannot instantiate UserManagementClient", error=exc)
            return None
    return _user_client

def _parse_color(color_input: str) -> Tuple[bool, Optional[str], Optional[str]]:
    if not color_input:
        return False, None, "Color is required (hex like `#FF0000` or a named color)."
    color_input = color_input.strip().lower()
    if color_input in COLOR_NAMES:
        return True, COLOR_NAMES[color_input], None
    hex_color = color_input.upper()
    if not hex_color.startswith('#'):
        hex_color = f"#{hex_color}"
    if re.match(r'^#[0-9A-F]{6}$', hex_color):
        return True, hex_color, None
    available_colors = ', '.join(list(COLOR_NAMES.keys())[:10]) + '...'
    return False, None, f"Invalid color. Use `#RRGGBB` or a named color ({available_colors})."

@CommandHandler.register('draw')
def handle_draw(interaction: dict = None):
    correlation_id = interaction.get('correlation_id') if interaction else None

    canvas_client = get_canvas_client()
    if not canvas_client.base_url:
        return create_error_embed("Service unavailable", "Canvas service is not configured.")

    user_id, username, avatar_url = extract_user_info(interaction)
    if not user_id:
        return create_error_embed("Unknown user", "Unable to resolve your Discord identity.")

    options = extract_options(interaction)
    x = options.get('x')
    y = options.get('y')
    color_input = options.get('color', 'black')

    if x is None or y is None:
        return create_error_embed(
            "Missing parameters",
            "Specify both `x` and `y` coordinates. Example: `/draw x:10 y:12 color:#FF0000`."
        )

    if not (0 <= x < CANVAS_SIZE and 0 <= y < CANVAS_SIZE):
        return create_error_embed(
            "Invalid coordinates",
            f"Coordinates must be between 0 and {CANVAS_SIZE - 1}."
        )

    ok, color_hex, color_error = _parse_color(color_input)
    if not ok or not color_hex:
        return create_error_embed("Invalid color", color_error or "Unsupported color value.")

    user_client = get_user_client()
    if not user_client:
        return create_error_embed("Service unavailable", "User service is unavailable. Please try again.")

    try:
        rate_limit = user_client.check_rate_limit(user_id, username, 'draw', correlation_id=correlation_id)
        if not rate_limit.get('allowed', True):
            return rate_limit_embed(rate_limit, 'draw')
    except Exception as exc:
        logger.warning("Rate limit check failed, allowing draw", error=exc, correlation_id=correlation_id, user_id=user_id)

    canvas_result = canvas_client.draw_pixel(x, y, color_hex, user_id, username, correlation_id)
    if not canvas_result.get('success'):
        return create_error_embed("Draw failed", canvas_result.get('error', 'Unexpected error while modifying the canvas.'))

    stats = {}
    try:
        new_total_draws = user_client.increment_usage(user_id, 'draw', correlation_id=correlation_id)
        if new_total_draws is not None:
            stats['total_draws'] = new_total_draws
            logger.debug(
                "Usage incremented successfully",
                correlation_id=correlation_id,
                user_id=user_id,
                total_draws=new_total_draws
            )
            user_stats = user_client.get_user_stats(user_id, correlation_id=correlation_id) or {}
            stats['is_premium'] = user_stats.get('is_premium', False)
            stats['is_banned'] = user_stats.get('is_banned', False)
        else:
            logger.warning("Increment usage returned None", correlation_id=correlation_id, user_id=user_id)
            stats = user_client.get_user_stats(user_id, correlation_id=correlation_id) or {}
    except Exception as exc:
        logger.warning("Failed to increment draw usage", error=exc, correlation_id=correlation_id, user_id=user_id)
        try:
            stats = user_client.get_user_stats(user_id, correlation_id=correlation_id) or {}
        except Exception:
            pass

    fields = []
    fields.append({'name': 'Coordinates', 'value': f'**X:** {x} | **Y:** {y}', 'inline': False})
    fields.append({'name': 'Color', 'value': f'`{color_hex}`', 'inline': True})
    if canvas_result.get('previous_color') and canvas_result.get('changed'):
        fields.append({'name': 'Previous Color', 'value': f'`{canvas_result["previous_color"]}`', 'inline': True})

    if stats.get('total_draws') is not None:
        fields.append({'name': 'Your Total Draws', 'value': f'**{stats["total_draws"]}** pixels', 'inline': True})
    if stats.get('is_premium'):
        fields.append({'name': 'Status', 'value': 'Premium', 'inline': True})

    description = "Pixel successfully placed on the shared 48×48 canvas!"
    if not canvas_result.get('changed'):
        description = "Pixel already had this color. No changes made."

    embed = create_embed(
        title='Pixel Placed Successfully',
        description=description,
        color=int(color_hex.replace('#', ''), 16),
        fields=fields,
        footer={'text': f'Artist: {username} • Canvas: 48×48'},
        thumbnail=create_user_thumbnail(avatar_url) if avatar_url else None,
        author=create_user_author(username, avatar_url) if avatar_url else None
    )
    return create_response(embed, ephemeral=False)

