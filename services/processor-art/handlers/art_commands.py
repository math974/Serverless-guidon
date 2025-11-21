"""Art commands (draw, snapshot, stats, colors) backed by CanvasManager."""
import re
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, Any
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from command_registry import CommandHandler  # noqa: E402
from shared.observability import init_observability  # noqa: E402
from shared.embed_utils import (  # noqa: E402
    create_error_embed,
    create_warning_embed,
    create_info_embed,
    create_success_embed,
    create_embed,
    create_response,
    extract_user_info,
    create_user_author,
    create_user_thumbnail,
    COLOR_PREMIUM,
    COLOR_SNAPSHOT,
    COLOR_COLORS,
    COLOR_INFO
)
from canvas_manager import CanvasManager
from user_client import UserManagementClient

logger, _ = init_observability('discord-processor-art-handlers', app=None)

# --- Global services --------------------------------------------------------
try:
    CANVAS_MANAGER = CanvasManager()
except Exception as exc:
    logger.error("Unable to initialize CanvasManager", error=exc)
    CANVAS_MANAGER = None

try:
    USER_CLIENT = UserManagementClient()
except Exception as exc:
    logger.warning("User-manager client unavailable", error=exc)
    USER_CLIENT = None

def _get_user_client() -> Optional[UserManagementClient]:
    global USER_CLIENT
    if USER_CLIENT is None:
        try:
            USER_CLIENT = UserManagementClient()
        except Exception as exc:
            logger.error("Cannot instantiate UserManagementClient", error=exc)
            return None
    return USER_CLIENT

COLOR_NAMES = {
    'red': '#FF0000',
    'green': '#00FF00',
    'blue': '#0000FF',
    'yellow': '#FFFF00',
    'orange': '#FFA500',
    'purple': '#800080',
    'pink': '#FFC0CB',
    'brown': '#A52A2A',
    'black': '#000000',
    'white': '#FFFFFF',
    'gray': '#808080',
    'grey': '#808080',
    'cyan': '#00FFFF',
    'magenta': '#FF00FF',
    'lime': '#00FF00',
    'navy': '#000080',
    'teal': '#008080',
    'maroon': '#800000',
    'olive': '#808000',
    'silver': '#C0C0C0',
    'gold': '#FFD700',
    'coral': '#FF7F50',
    'salmon': '#FA8072',
    'khaki': '#F0E68C',
    'violet': '#EE82EE',
    'indigo': '#4B0082',
    'turquoise': '#40E0D0',
    'crimson': '#DC143C'
}


# --- Helper utilities -------------------------------------------------------
def _extract_options(interaction: Optional[dict]) -> Dict[str, Any]:
    options = {}
    if not interaction:
        return options
    for option in interaction.get('data', {}).get('options', []):
            options[option['name']] = option.get('value')
    return options


# Use shared extract_user_info
_extract_user_info = extract_user_info


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


# Use shared create_error_embed
_error_embed = create_error_embed


def _rate_limit_embed(result: Dict[str, Any], command_label: str) -> dict:
    """Create rate limit warning embed."""
    reset_time = result.get('reset_in', 0)
    minutes = reset_time // 60
    seconds = reset_time % 60
    time_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

    return create_warning_embed(
        title='Rate Limit Exceeded',
        description=f'You have reached the maximum limit for `{command_label}` commands.\n\n**Please wait:** {time_str}',
        fields=[
            {
                'name': 'Current Status',
                'value': f'**Remaining:** {result.get("remaining", 0)}/{result.get("max", 0)}\n**Reset in:** {time_str}',
                'inline': False
            }
        ],
        footer={'text': 'Tip: Premium users enjoy larger rate limits'},
        ephemeral=True
    )


# --- Commands ---------------------------------------------------------------
@CommandHandler.register('draw')
def handle_draw(interaction: dict = None):
    correlation_id = interaction.get('correlation_id') if interaction else None

    if CANVAS_MANAGER is None:
        return _error_embed("Service unavailable", "Canvas backend is warming up, please try again shortly.")

    user_id, username, avatar_url = _extract_user_info(interaction)
    if not user_id:
        return _error_embed("Unknown user", "Unable to resolve your Discord identity.")

    options = _extract_options(interaction)
    x = options.get('x')
    y = options.get('y')
    color_input = options.get('color', 'black')

    if x is None or y is None:
        return _error_embed(
            "Missing parameters",
            "Specify both `x` and `y` coordinates. Example: `/draw x:10 y:12 color:#FF0000`."
        )

    if not (0 <= x < CANVAS_MANAGER.CANVAS_SIZE and 0 <= y < CANVAS_MANAGER.CANVAS_SIZE):
        return _error_embed(
            "Invalid coordinates",
            f"Coordinates must be between 0 and {CANVAS_MANAGER.CANVAS_SIZE - 1}."
        )

    ok, color_hex, color_error = _parse_color(color_input)
    if not ok or not color_hex:
        return _error_embed("Invalid color", color_error or "Unsupported color value.")

    user_client = _get_user_client()
    if not user_client:
        return _error_embed("Service unavailable", "User service is unavailable. Please try again.")

    try:
        rate_limit = user_client.check_rate_limit(user_id, username, 'draw', correlation_id=correlation_id)
        if not rate_limit.get('allowed', True):
            return _rate_limit_embed(rate_limit, 'draw')
    except Exception as exc:
        logger.warning(
            "Rate limit check failed, allowing draw",
            error=exc,
            correlation_id=correlation_id,
            user_id=user_id
        )

    canvas_result = CANVAS_MANAGER.draw_pixel(x, y, color_hex, user_id, username)
    if not canvas_result.get('success'):
        return _error_embed("Draw failed", canvas_result.get('error', 'Unexpected error while modifying the canvas.'))

    try:
        user_client.increment_usage(user_id, 'draw', correlation_id=correlation_id)
    except Exception as exc:
        logger.warning(
            "Failed to increment draw usage",
            error=exc,
            correlation_id=correlation_id,
            user_id=user_id
        )

    stats = user_client.get_user_stats(user_id, correlation_id=correlation_id) or {}

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

@CommandHandler.register('snapshot')
def handle_snapshot(interaction: dict = None):
    correlation_id = interaction.get('correlation_id') if interaction else None

    if CANVAS_MANAGER is None:
        return _error_embed("Service unavailable", "Snapshot backend is temporarily unavailable.")

    user_id, username, avatar_url = _extract_user_info(interaction)
    if not user_id:
        return _error_embed("Unknown user", "Unable to resolve your Discord identity.")

    user_client = _get_user_client()
    if not user_client:
        return _error_embed("Service unavailable", "User service is unavailable. Please try again.")

    try:
        rate_limit = user_client.check_rate_limit(user_id, username, 'snapshot', correlation_id=correlation_id)
        if not rate_limit.get('allowed', True):
            return _rate_limit_embed(rate_limit, 'snapshot')
    except Exception as exc:
        logger.warning(
            "Snapshot rate-limit check failed, allowing command",
            error=exc,
            correlation_id=correlation_id,
            user_id=user_id
        )

    result = CANVAS_MANAGER.create_snapshot(user_id, username)
    if not result.get('success'):
        return _error_embed("Snapshot failed", result.get('error', 'Could not generate the snapshot.'))

    try:
        user_client.increment_usage(user_id, 'snapshot', correlation_id=correlation_id)
    except Exception as exc:
        logger.warning(
            "Failed to increment snapshot usage",
            error=exc,
            correlation_id=correlation_id,
            user_id=user_id
        )

    snapshot_url = result.get('public_url')

    fields = [
        {
            'name': 'Image Details',
            'value': f'**Size:** {result.get("image_size", 480)}×{result.get("image_size", 480)} px\n**Total Pixels:** {result.get("pixel_count", 2304)}',
                        'inline': False
        }
    ]

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


@CommandHandler.register('canvas_state')
def handle_canvas_state(interaction: dict = None):
    """Return the full canvas matrix for web rendering."""
    correlation_id = interaction.get('correlation_id') if interaction else None

    if CANVAS_MANAGER is None:
        logger.warning("CanvasManager unavailable for canvas_state", correlation_id=correlation_id)
        return {
            'status': 'error',
            'message': 'Canvas backend is unavailable. Please try again shortly.'
        }

    try:
        canvas_array = CANVAS_MANAGER.get_canvas_array()
        stats = CANVAS_MANAGER.get_canvas_stats()

        if stats.get('last_update') and hasattr(stats['last_update'], 'isoformat'):
            stats['last_update'] = stats['last_update'].isoformat()

        payload = {
            'size': CANVAS_MANAGER.CANVAS_SIZE,
            'pixels': canvas_array,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'stats': stats
        }

        pixel_count = sum(len(row) for row in canvas_array) if canvas_array else 0
        logger.info(
            "Canvas state generated",
            correlation_id=correlation_id,
            pixel_count=pixel_count
        )

        return {
            'status': 'success',
            'canvas': payload,
            'stats': stats
        }
    except Exception as exc:
        logger.error(
            "Failed to build canvas state",
            error=exc,
            correlation_id=correlation_id
        )
        return {
            'status': 'error',
            'message': 'Failed to load canvas state.'
        }


@CommandHandler.register('stats')
def handle_stats(interaction: dict = None):
    correlation_id = interaction.get('correlation_id') if interaction else None
    user_id, username, avatar_url = _extract_user_info(interaction)

    if not user_id or CANVAS_MANAGER is None:
        return _error_embed("Unavailable", "Unable to retrieve statistics right now.")

    user_client = _get_user_client()
    if not user_client:
        return _error_embed("Service unavailable", "User service is unavailable. Please try again.")

    try:
        user_stats = user_client.get_user_stats(user_id, correlation_id=correlation_id)
        canvas_stats = CANVAS_MANAGER.get_canvas_stats()
        draw_limits = user_client.get_rate_limit_info(user_id, 'draw', correlation_id=correlation_id)
    except Exception as exc:
        logger.error("Failed to fetch stats", error=exc, correlation_id=correlation_id, user_id=user_id)
        return _error_embed("Error", "Could not load statistics.")

    is_premium = user_stats.get('is_premium', False)
    tier_label = 'Premium' if is_premium else 'Standard'

    fields = []

    # - User information -
    fields.append({
        'name': 'Your Account',
        'value': f'**Tier:** {tier_label}\n**Your Pixels:** {user_stats.get("total_draws", 0)}',
        'inline': False
    })

    # - Rate limits -
    fields.append({
        'name': 'Rate Limits',
        'value': f'**Draws remaining:** {draw_limits.get("remaining", 0)}/{draw_limits.get("max", 0)}',
        'inline': False
    })

    # - Canvas statistics -
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


@CommandHandler.register('colors')
def handle_colors(interaction: dict = None):
    """Display available color names and quick usage examples."""
    groups = {
        'Basics': ['red', 'green', 'blue', 'yellow', 'black', 'white'],
        'Pastels': ['pink', 'salmon', 'coral', 'violet', 'turquoise', 'khaki'],
        'Dark tones': ['navy', 'teal', 'maroon', 'olive', 'indigo', 'crimson'],
        'Metallic': ['gold', 'silver']
    }

    fields = []
    for label, items in groups.items():
        valid_items = [c for c in items if c in COLOR_NAMES]
        if not valid_items:
            continue
        color_list = ', '.join(f'`{c}`' for c in valid_items)
        fields.append({'name': label, 'value': color_list, 'inline': False})

    fields.append({
        'name': 'Usage Examples',
        'value': '```\n/draw x:10 y:10 color:red\n/draw x:10 y:10 color:#FFAA00\n```',
        'inline': False
    })

    embed = create_embed(
        title='Available Colors',
        description=f'You can use **{len(COLOR_NAMES)} named colors** or any **hex code** format `#RRGGBB`.\n\nChoose from the categories below or use your own hex color.',
        color=COLOR_COLORS,
        fields=fields,
        footer={'text': 'Tip: Use /draw x:<number> y:<number> color:<name or hex> to place pixels'}
    )
    return create_response(embed, ephemeral=True)
