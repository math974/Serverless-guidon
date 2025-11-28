"""Canvas Service - REST API for canvas operations."""
import os
import sys
from flask import Request, jsonify, make_response
import functions_framework
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.observability import init_observability, traced_function
from shared.correlation import with_correlation
from shared.auth_utils import verify_service_auth
from canvas_manager import CanvasManager
from shared.user_client import UserManagementClient

logger, tracing = init_observability('canvas-service', app=None)

_canvas_manager = None
_user_client = None

def get_canvas_manager():
    """Get or create CanvasManager instance."""
    global _canvas_manager
    if _canvas_manager is None:
        _canvas_manager = CanvasManager()
    return _canvas_manager

def get_user_client():
    """Get or create UserManagementClient instance."""
    global _user_client
    if _user_client is None:
        try:
            _user_client = UserManagementClient()
        except Exception as e:
            logger.warning("Failed to initialize UserManagementClient", error=e)
            _user_client = None
    return _user_client


def add_cors_headers(response):
    """Add CORS headers to response."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Session-ID, X-Correlation-ID, Authorization'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response


@functions_framework.http
@with_correlation(logger)
@traced_function("canvas_service")
def canvas_service(request: Request):
    """Main entry point for canvas service."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = make_response('', 200)
        return add_cors_headers(response)

    try:
        path = request.path.rstrip('/')
        method = request.method

        logger.info("Canvas service request", correlation_id=correlation_id, path=path, method=method)

        # --- Health check ---
        if path == '/health' and method == 'GET':
            return health_handler(request, correlation_id)

        is_valid, error_msg = verify_service_auth(request, expected_audience=None, logger_instance=logger)
        if not is_valid:
            logger.warning(
                "Authentication failed",
                correlation_id=correlation_id,
                path=path,
                error=error_msg
            )
            response = jsonify({
                'error': 'Unauthorized',
                'message': error_msg or 'Authentication required'
            }), 401
            return add_cors_headers(response)

        # --- Draw pixel ---
        if path == '/canvas/draw' and method == 'POST':
            return draw_pixel_handler(request, correlation_id)

        # --- Canvas state (array) ---
        if path == '/canvas/state' and method == 'GET':
            return get_canvas_state_handler(request, correlation_id)

        # --- Create snapshot ---
        if path == '/canvas/snapshot' and method == 'POST':
            return create_snapshot_handler(request, correlation_id)

        # --- Get canvas stats ---
        if path == '/canvas/stats' and method == 'GET':
            return get_canvas_stats_handler(request, correlation_id)

        # --- Get pixel info ---
        if path.startswith('/canvas/pixel/') and method == 'GET':
            parts = path.split('/')
            if len(parts) == 5:
                try:
                    x = int(parts[3])
                    y = int(parts[4])
                    return get_pixel_info_handler(request, correlation_id, x, y)
                except (ValueError, IndexError):
                    pass

        logger.warning("Unknown path", correlation_id=correlation_id, path=path, method=method)
        response = jsonify({'error': 'Not found'}), 404
        return add_cors_headers(response)

    except Exception as e:
        logger.error("Error in canvas_service", error=e, correlation_id=correlation_id, path=request.path)
        response = jsonify({'error': 'Internal server error'}), 500
        return add_cors_headers(response)


def health_handler(request: Request, correlation_id: str = None):
    """Health check endpoint."""
    canvas_manager = get_canvas_manager()
    return jsonify({
        'status': 'healthy',
        'service': 'canvas-service',
        'canvas_size': canvas_manager.CANVAS_SIZE,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200


def draw_pixel_handler(request: Request, correlation_id: str = None):
    """Handle POST /canvas/draw - Draw a pixel."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'error': 'Missing JSON body'}), 400

        x = data.get('x')
        y = data.get('y')
        color = data.get('color')
        user_id = data.get('user_id')
        username = data.get('username')

        if x is None or y is None or not color or not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: x, y, color, user_id'
            }), 400

        canvas_manager = get_canvas_manager()
        result = canvas_manager.draw_pixel(x, y, color, user_id, username)

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error("Error in draw_pixel_handler", error=e, correlation_id=correlation_id)
        return jsonify({'success': False, 'error': str(e)}), 500


def get_canvas_state_handler(request: Request, correlation_id: str = None):
    """Handle GET /canvas/state - Get canvas as 2D array."""
    try:
        canvas_manager = get_canvas_manager()
        canvas_array = canvas_manager.get_canvas_array()
        user_client = get_user_client()
        stats = canvas_manager.get_canvas_stats(user_client=user_client, correlation_id=correlation_id)

        # Convert Firestore timestamps to ISO strings
        if stats.get('last_update') and hasattr(stats['last_update'], 'isoformat'):
            stats['last_update'] = stats['last_update'].isoformat()

        return jsonify({
            'size': canvas_manager.CANVAS_SIZE,
            'pixels': canvas_array,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'stats': stats
        }), 200

    except Exception as e:
        logger.error("Error in get_canvas_state_handler", error=e, correlation_id=correlation_id)
        return jsonify({'error': str(e)}), 500


def create_snapshot_handler(request: Request, correlation_id: str = None):
    """Handle POST /canvas/snapshot - Create a snapshot."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        username = data.get('username')

        canvas_manager = get_canvas_manager()
        result = canvas_manager.create_snapshot(user_id, username)

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error("Error in create_snapshot_handler", error=e, correlation_id=correlation_id)
        return jsonify({'success': False, 'error': str(e)}), 500


def get_canvas_stats_handler(request: Request, correlation_id: str = None):
    """Handle GET /canvas/stats - Get canvas statistics."""
    try:
        canvas_manager = get_canvas_manager()
        user_client = get_user_client()
        stats = canvas_manager.get_canvas_stats(user_client=user_client, correlation_id=correlation_id)

        # Convert Firestore timestamps to ISO strings
        if stats.get('last_update') and hasattr(stats['last_update'], 'isoformat'):
            stats['last_update'] = stats['last_update'].isoformat()

        return jsonify(stats), 200

    except Exception as e:
        logger.error("Error in get_canvas_stats_handler", error=e, correlation_id=correlation_id)
        return jsonify({'error': str(e)}), 500


def get_pixel_info_handler(request: Request, correlation_id: str = None, x: int = None, y: int = None):
    """Handle GET /canvas/pixel/{x}/{y} - Get pixel information."""
    try:
        if x is None or y is None:
            # Try to get from query params
            x = request.args.get('x', type=int)
            y = request.args.get('y', type=int)

        if x is None or y is None:
            return jsonify({'error': 'Missing x or y parameter'}), 400

        canvas_manager = get_canvas_manager()
        pixel_info = canvas_manager.get_pixel_info(x, y)

        if pixel_info:
            # Convert Firestore timestamps to ISO strings
            if pixel_info.get('timestamp') and hasattr(pixel_info['timestamp'], 'isoformat'):
                pixel_info['timestamp'] = pixel_info['timestamp'].isoformat()
            return jsonify(pixel_info), 200
        else:
            return jsonify({'error': 'Invalid coordinates'}), 400

    except Exception as e:
        logger.error("Error in get_pixel_info_handler", error=e, correlation_id=correlation_id)
        return jsonify({'error': str(e)}), 500

