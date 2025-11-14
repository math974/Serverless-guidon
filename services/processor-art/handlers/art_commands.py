"""Art-related Discord commands (draw, snapshot)."""
from datetime import datetime, timezone
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from command_registry import CommandHandler  # noqa: E402


@CommandHandler.register('draw')
def handle_draw(interaction: dict = None):
    """Handle draw command - draw a pixel.

    Args:
        interaction: Discord interaction data containing command options
    """
    # Extract options from interaction
    options = {}
    if interaction and 'data' in interaction and 'options' in interaction['data']:
        for option in interaction['data']['options']:
            options[option['name']] = option.get('value')

    x = options.get('x')
    y = options.get('y')
    color = options.get('color', '#000000')

    # TODO: Implement actual drawing logic here
    # For now, just return a confirmation

    description = f"Drawing pixel at ({x}, {y}) with color {color}"
    if not all([x, y]):
        description = "Missing required parameters. Usage: `/draw x:<number> y:<number> color:<hex>`"

    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': 'Draw Pixel',
                'description': description,
                'color': 0xFF6B6B,
                'fields': [
                    {
                        'name': 'Coordinates',
                        'value': f'X: {x or "N/A"}, Y: {y or "N/A"}',
                        'inline': True
                    },
                    {
                        'name': 'Color',
                        'value': color or 'N/A',
                        'inline': True
                    }
                ],
                'footer': {
                    'text': 'Art Commands - Under Development'
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }]
        }
    }


@CommandHandler.register('snapshot')
def handle_snapshot():
    """Handle snapshot command - take a snapshot of the canvas."""
    return {
        'type': 4,
        'data': {
            'embeds': [{
                'title': 'Snapshot',
                'description': 'Take a snapshot of the current canvas state. This command is under development.',
                'color': 0x4ECDC4,
                'fields': [
                    {
                        'name': 'Usage',
                        'value': '`/snapshot` - Captures the current canvas',
                        'inline': False
                    }
                ],
                'footer': {
                    'text': 'Art Commands - Coming Soon'
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }]
        }
    }

