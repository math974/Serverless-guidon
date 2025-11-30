"""Authentication utilities for service-to-service communication."""
import os
from typing import Optional, Tuple
from flask import Request, jsonify
from shared.observability import init_observability

logger, _ = init_observability('auth-utils', app=None)


def get_service_url_from_request(request: Request) -> Optional[str]:
    """Get the full service URL from the request.

    Args:
        request: Flask request object

    Returns:
        Full service URL (e.g., https://service-name-xxx.a.run.app) or None
    """
    host = request.headers.get('Host')
    if host:
        scheme = request.headers.get('X-Forwarded-Proto', 'https')
        if ':' in host:
            host = host.split(':')[0]
        return f"{scheme}://{host}"
    return None


def verify_service_auth(request: Request, expected_audience: Optional[str] = None, logger_instance=None) -> Tuple[bool, Optional[str]]:
    """Verify Google Cloud identity token from request headers.

    Args:
        request: Flask request object
        expected_audience: Optional expected audience (service URL)
        logger_instance: Optional logger instance for error logging

    Returns:
        Tuple of (is_valid: bool, error_message: str or None)
    """
    log = logger_instance or logger

    if request.path == '/health' and request.method == 'GET':
        return True, None

    if request.method == 'OPTIONS':
        return True, None

    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        log.warning("Missing or invalid Authorization header", path=request.path)
        return False, "Missing or invalid Authorization header"

    token = auth_header[7:]

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        request_session = google_requests.Request()

        if not expected_audience:
            expected_audience = get_service_url_from_request(request)

            if not expected_audience:
                log.error(
                    "Could not determine expected audience from request Host header",
                    path=request.path,
                    host=request.headers.get('Host')
                )
                return False, "Could not determine expected audience from request"

        if expected_audience:
            expected_audience = expected_audience.rstrip('/')
            if expected_audience.startswith('http://'):
                expected_audience = expected_audience.replace('http://', 'https://', 1)

        claims = id_token.verify_token(token, request_session, audience=expected_audience)

        log.debug(
            "Token verified successfully",
            path=request.path,
            email=claims.get('email'),
            expected_audience=expected_audience,
            token_audience=claims.get('aud')
        )

        return True, None
    except ValueError as e:
        error_msg = str(e)
        if 'audience' in error_msg.lower() or 'aud' in error_msg.lower():
            log.warning(
                "Token audience mismatch",
                path=request.path,
                expected_audience=expected_audience,
                error=error_msg
            )
            return False, f"Invalid token: Token audience mismatch. Expected: {expected_audience}"
        log.warning("Invalid token", error=e, path=request.path, expected_audience=expected_audience)
        return False, f"Invalid token: {error_msg}"
    except Exception as e:
        log.error("Error verifying token", error=e, path=request.path)
        return False, f"Token verification error: {str(e)}"


def require_auth(expected_audience: Optional[str] = None):
    """Decorator to require authentication for a Flask route.

    Args:
        expected_audience: Optional expected audience (service URL)

    Usage:
        @require_auth()
        def my_handler(request):
            ...
    """
    def decorator(func):
        def wrapper(request: Request, *args, **kwargs):
            is_valid, error_msg = verify_service_auth(request, expected_audience, logger)
            if not is_valid:
                correlation_id = getattr(request, 'correlation_id', request.headers.get('X-Correlation-ID'))
                logger.warning(
                    "Authentication failed",
                    correlation_id=correlation_id,
                    path=request.path,
                    error=error_msg
                )
                return jsonify({
                    'error': 'Unauthorized',
                    'message': error_msg or 'Authentication required'
                }), 401
            return func(request, *args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
