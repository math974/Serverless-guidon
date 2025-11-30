"""Pixel info command handler."""
import os
import sys
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from command_registry import CommandHandler
from shared.observability import init_observability
from shared.embed_utils import (
    create_error_embed,
    create_embed,
    create_response,
    CANVAS_SIZE,
    extract_options,
)
from shared.canvas_client import CanvasClient

logger, _ = init_observability('processor-pixel-info-handler', app=None)

_canvas_client = None

def get_canvas_client():
    global _canvas_client
    if _canvas_client is None:
        try:
            _canvas_client = CanvasClient()
        except Exception as exc:
            logger.error("Cannot instantiate CanvasClient", error=exc)
            return None
    return _canvas_client

@CommandHandler.register('pixel_info')
@CommandHandler.register('getpixel')
def handle_pixel_info(interaction: dict = None):
    correlation_id = interaction.get('correlation_id') if interaction else None

    canvas_client = get_canvas_client()
    if not canvas_client:
        return create_error_embed("Service unavailable", "Canvas service is not configured.")

    options = extract_options(interaction)
    x = options.get('x')
    y = options.get('y')

    if x is None or y is None:
        return create_error_embed(
            "Missing parameters",
            "Specify both `x` and `y` coordinates. Example: `/pixel_info x:10 y:12`."
        )

    # Get canvas size dynamically
    canvas_state = canvas_client.get_canvas_state(correlation_id=correlation_id)
    if canvas_state.get('error'):
        return create_error_embed("Service unavailable", "Unable to retrieve canvas information.")

    canvas_size = canvas_state.get('size', CANVAS_SIZE)  # Fallback to default if not available
    if not isinstance(canvas_size, int) or canvas_size <= 0:
        canvas_size = CANVAS_SIZE  # Fallback to default

    if not (0 <= x < canvas_size and 0 <= y < canvas_size):
        return create_error_embed(
            "Invalid coordinates",
            f"Coordinates must be between 0 and {canvas_size - 1} (canvas size: {canvas_size}×{canvas_size})."
        )

    pixel_info = canvas_client.get_pixel_info(x, y, correlation_id)

    if not pixel_info:
        return create_error_embed("Error", "Failed to retrieve pixel information.")

    fields = []
    fields.append({
        'name': 'Coordinates',
        'value': f'**X:** {x} | **Y:** {y}',
        'inline': False
    })
    fields.append({
        'name': 'Color',
        'value': f'`{pixel_info.get("color", "#FFFFFF")}`',
        'inline': True
    })

    if pixel_info.get('username') and pixel_info.get('username') != 'Empty':
        fields.append({
            'name': 'Drawn by',
            'value': f'**{pixel_info.get("username", "Unknown")}**',
            'inline': True
        })

    if pixel_info.get('timestamp'):
        timestamp_str = pixel_info['timestamp']
        if isinstance(timestamp_str, str):
            fields.append({
                'name': 'Last updated',
                'value': timestamp_str[:19] if len(timestamp_str) > 19 else timestamp_str,
                'inline': False
            })

    if pixel_info.get('edit_count'):
        fields.append({
            'name': 'Edit count',
            'value': f'**{pixel_info.get("edit_count", 0)}** times',
            'inline': True
        })

    embed = create_embed(
        title='Pixel Information',
        description=f'Details for pixel at ({x}, {y})',
        color=int(pixel_info.get('color', '#FFFFFF').replace('#', ''), 16) if pixel_info.get('color', '#FFFFFF').startswith('#') else 0xFFFFFF,
        fields=fields,
        footer={'text': f'Canvas: {canvas_size}×{canvas_size}'}
    )
    response = create_response(embed, ephemeral=True)

    if isinstance(response, dict):
        response['pixel_info'] = {
            'x': x,
            'y': y,
            'coordinates': f'({x}, {y})',
            'color': pixel_info.get('color', '#FFFFFF'),
            'drawnBy': pixel_info.get('username', 'Empty'),
            'lastUpdated': pixel_info.get('timestamp'),
            'editCount': pixel_info.get('edit_count', 0),
            'user_id': pixel_info.get('user_id'),
            'userId': pixel_info.get('user_id'),
            'avatar': None
        }

    return response

