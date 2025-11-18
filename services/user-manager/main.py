"""
User Management Service with Functions Framework for Cloud Functions Gen2
Handles user CRUD, rate limiting, bans, premium, stats
"""
import functions_framework
from flask import Request, jsonify
from shared.correlation import with_correlation
from shared.observability import init_observability, traced_function
from cache import cache
from handlers import handle_users, handle_rate_limit, handle_stats

logger, tracing = init_observability('user-management-service', app=None)


@functions_framework.http
@with_correlation(logger)
@traced_function("user_management_handler")
def user_management_handler(request: Request):
    """Main HTTP handler for user management.

    Args:
        request: HTTP request object

    Returns:
        HTTP response object
    """
    path = request.path
    method = request.method
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    # CORS headers
    if method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE',
            'Access-Control-Allow-Headers': 'Content-Type, X-Correlation-ID',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    try:
        # --- Health check ---
        if path == '/health' and method == 'GET':
            return handle_health(request)

        # --- User Management Routes ---
        elif path.startswith('/api/users'):
            return handle_users(request, path, method)

        # --- Rate Limiting Routes ---
        elif path.startswith('/api/rate-limit'):
            return handle_rate_limit(request, path, method)

        # --- Stats Routes ---
        elif path.startswith('/api/stats'):
            return handle_stats(request, path, method)

        else:
            logger.warning(
                "Unknown path requested",
                correlation_id=correlation_id,
                path=path,
                method=method
            )
            return jsonify({
                'error': 'Not Found',
                'path': path,
                'method': method
            }), 404

    except Exception as e:
        logger.error(
            "Unhandled error in user management handler",
            error=e,
            correlation_id=correlation_id,
            path=path,
            method=method
        )
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Internal Server Error',
            'details': str(e)
        }), 500


@traced_function("handle_health")
def handle_health(request: Request):
    """Health check endpoint."""
    correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))

    logger.info(
        "Health check called",
        correlation_id=correlation_id
    )

    return jsonify({
        'status': 'healthy',
        'service': 'user-management-service',
        'framework': 'functions_framework',
        'cache_size': cache.size()
    }), 200
