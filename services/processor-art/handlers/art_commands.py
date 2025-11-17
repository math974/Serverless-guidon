"""Art commands (draw, snapshot, stats, colors) backed by CanvasManager."""
import re
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, Any
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from command_registry import CommandHandler  # noqa: E402
from shared.observability import init_observability  # noqa: E402
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


def _extract_user_info(interaction: Optional[dict]) -> Tuple[Optional[str], Optional[str]]:
    if not interaction:
        return None, None
    user_payload = interaction.get('member', {}).get('user') or interaction.get('user', {})
    if not user_payload:
        return None, None
    username = user_payload.get('username', 'Unknown')
    discriminator = user_payload.get('discriminator')
    if discriminator and discriminator != '0':
        username = f"{username}#{discriminator}"
    return user_payload.get('id'), username


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


def _error_embed(title: str, description: str, ephemeral: bool = True) -> dict:
    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': f'❌ {title}',
                'description': description,
                'color': 0xFF4C4C,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }],
            'flags': 64 if ephemeral else 0
        }
    }


def _rate_limit_embed(result: Dict[str, Any], command_label: str) -> dict:
    reset_time = result.get('reset_in', 0)
    minutes = reset_time // 60
    seconds = reset_time % 60
    time_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': '⏱️ Rate limit exceeded',
                'description': f'You have reached the limit for `{command_label}`.\nPlease wait **{time_str}**.',
                'color': 0xFF6B6B,
                'fields': [
                    {
                        'name': 'Remaining',
                        'value': f"{result.get('remaining', 0)}/{result.get('max', 0)}",
                        'inline': True
                    },
                    {
                        'name': 'Reset in',
                        'value': time_str,
                        'inline': True
                    }
                ],
                'footer': {
                    'text': 'Tip: premium users enjoy larger limits.'
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }],
            'flags': 64
        }
    }


# --- Commands ---------------------------------------------------------------
@CommandHandler.register('draw')
def handle_draw(interaction: dict = None):
    correlation_id = interaction.get('correlation_id') if interaction else None

    if CANVAS_MANAGER is None:
        return _error_embed("Service unavailable", "Canvas backend is warming up, please try again shortly.")

    user_id, username = _extract_user_info(interaction)
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

    fields = [
        {'name': '📍 Position', 'value': f'X: {x} / Y: {y}', 'inline': True},
        {'name': '🎨 Color', 'value': color_hex, 'inline': True},
        {'name': '👤 Artist', 'value': username, 'inline': True}
    ]
    if stats.get('total_draws') is not None:
        fields.append({'name': '🎯 Total draws', 'value': str(stats['total_draws']), 'inline': True})
    if stats.get('is_premium'):
        fields.append({'name': '💎 Status', 'value': 'Premium', 'inline': True})
    if canvas_result.get('previous_color') and canvas_result.get('changed'):
        fields.append({'name': 'Previous color', 'value': canvas_result['previous_color'], 'inline': True})

    description = "Pixel stored on the shared 48x48 canvas."
    if not canvas_result.get('changed'):
        description += "\n*(Pixel already had this color)*"

    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': '🎨 Pixel placed!',
                'description': description,
                'color': int(color_hex.replace('#', ''), 16),
                'fields': fields,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }]
        }
    }

@CommandHandler.register('snapshot')
def handle_snapshot(interaction: dict = None):
    correlation_id = interaction.get('correlation_id') if interaction else None

    if CANVAS_MANAGER is None:
        return _error_embed("Service unavailable", "Snapshot backend is temporarily unavailable.")

    user_id, username = _extract_user_info(interaction)
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
        {'name': '📏 Size', 'value': f"{result.get('image_size', 480)} px", 'inline': True},
        {'name': '🎨 Pixels', 'value': str(result.get('pixel_count', 2304)), 'inline': True}
    ]
    if snapshot_url and snapshot_url.startswith('http'):
        fields.append({'name': '🔗 Download', 'value': f'[Open in browser]({snapshot_url})', 'inline': False})

    embed = {
        'title': '📸 Canvas snapshot created!',
        'description': f'Snapshot captured by **{username}**',
        'color': 0x4ECDC4,
        'fields': fields,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    if snapshot_url and (snapshot_url.startswith('http://') or snapshot_url.startswith('https://')):
        embed['image'] = {'url': snapshot_url}
        embed['thumbnail'] = {'url': snapshot_url}

    return {
        'type': 4,
        'data': {
            'embeds': [embed]
        }
    }

@CommandHandler.register('stats')
def handle_stats(interaction: dict = None):
    correlation_id = interaction.get('correlation_id') if interaction else None
    user_id, username = _extract_user_info(interaction)

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
    tier_icon = '⭐' if is_premium else '🔵'

    fields = [
        {'name': '🎖️ Tier', 'value': f'{tier_icon} {tier_label}', 'inline': True},
        {'name': '🎨 Your pixels', 'value': str(user_stats.get('total_draws', 0)), 'inline': True},
        {
            'name': '⏱️ Draw limit',
            'value': f"{draw_limits.get('remaining', 0)}/{draw_limits.get('max', 0)}",
            'inline': True
        },
        {'name': '🧮 Canvas pixels', 'value': str(canvas_stats.get('total_pixels', 0)), 'inline': True},
        {'name': '👥 Contributors', 'value': str(canvas_stats.get('unique_contributors', 0)), 'inline': True}
    ]

    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': f'📊 Stats for {username}',
                'color': 0xFFD700 if is_premium else 0x0066CC,
                'fields': fields,
                'footer': {
                    'text': 'Use /draw and /snapshot to climb the leaderboard!'
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }],
            'flags': 64
        }
    }


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
        fields.append({'name': f'🎨 {label}', 'value': color_list, 'inline': False})

    fields.append({
        'name': 'Usage',
        'value': '`/draw x:10 y:10 color:red`\n`/draw x:10 y:10 color:#FFAA00`',
        'inline': False
    })

    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': 'Available colors',
                'description': f'Use {len(COLOR_NAMES)} named colors or any hex code `#RRGGBB`.',
                'color': 0x00AAFF,
                'fields': fields,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }],
            'flags': 64
        }
    }
