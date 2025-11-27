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
        _canvas_client = CanvasClient()
    return _canvas_client

@CommandHandler.register('pixel_info')
@CommandHandler.register('getpixel')
def handle_pixel_info(interaction: dict = None):
    correlation_id = interaction.get('correlation_id') if interaction else None

    canvas_client = get_canvas_client()
    if not canvas_client.base_url:
        return create_error_embed("Service unavailable", "Canvas service is not configured.")

    options = extract_options(interaction)
    x = options.get('x')
    y = options.get('y')

    if x is None or y is None:
        return create_error_embed(
            "Missing parameters",
            "Specify both `x` and `y` coordinates. Example: `/pixel_info x:10 y:12`."
        )

    if not (0 <= x < CANVAS_SIZE and 0 <= y < CANVAS_SIZE):
        return create_error_embed(
            "Invalid coordinates",
            f"Coordinates must be between 0 and {CANVAS_SIZE - 1}."
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
        footer={'text': 'Canvas: 48×48'}
    )
    return create_response(embed, ephemeral=True)

