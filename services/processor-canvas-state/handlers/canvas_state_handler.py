"""Canvas state command handler."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from command_registry import CommandHandler
from shared.observability import init_observability
from shared.canvas_client import CanvasClient

logger, _ = init_observability('processor-canvas-state-handler', app=None)

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

@CommandHandler.register('canvas_state')
def handle_canvas_state(interaction: dict = None):
    """Return the full canvas matrix for web rendering."""
    correlation_id = interaction.get('correlation_id') if interaction else None

    canvas_client = get_canvas_client()
    if not canvas_client:
        logger.warning("Canvas service URL not configured for canvas_state", correlation_id=correlation_id)
        return {
            'status': 'error',
            'message': 'Canvas backend is unavailable. Please try again shortly.'
        }

    try:
        canvas_data = canvas_client.get_canvas_state(correlation_id)

        if 'error' in canvas_data:
            return {
                'status': 'error',
                'message': canvas_data.get('error', 'Failed to load canvas state.')
            }

        pixel_count = sum(len(row) for row in canvas_data.get('pixels', [])) if canvas_data.get('pixels') else 0
        logger.info(
            "Canvas state generated",
            correlation_id=correlation_id,
            pixel_count=pixel_count
        )

        return {
            'status': 'success',
            'canvas': canvas_data,
            'stats': canvas_data.get('stats', {})
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

