"""Colors command handler."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from command_registry import CommandHandler
from shared.observability import init_observability
from shared.embed_utils import create_embed, create_response, COLOR_COLORS, COLOR_NAMES

logger, _ = init_observability('processor-colors-handler', app=None)

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

