"""Request correlation and logging utilities for Functions Framework and Flask apps.
"""
import time
from functools import wraps
from typing import Callable

def with_correlation(logger):
    """Decorator to handle correlation ID and request logging.

    Supports both Cloud Functions (with explicit request parameter) and Flask apps
    (using flask.request context).

    Usage for Cloud Functions:
        @with_correlation(logger)
        def my_handler(request: Request):
            # correlation_id is automatically available via request.correlation_id
            ...

    Usage for Flask:
        @with_correlation(logger)
        @app.route('/path')
        def my_handler():
            # correlation_id is automatically available via flask.request.correlation_id
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from shared.observability import get_correlation_id

            # Detect if we're in a Flask context or Cloud Functions context
            # Try to get request from Flask context first
            try:
                from flask import request as flask_request
                # Check if we're in a Flask request context
                if hasattr(flask_request, 'method'):
                    req = flask_request
                    is_flask = True
                else:
                    req = None
                    is_flask = False
            except (RuntimeError, ImportError):
                # Not in Flask context
                req = None
                is_flask = False

            # If not Flask, try to get request from first positional argument (Cloud Functions)
            if not is_flask and args and hasattr(args[0], 'method') and hasattr(args[0], 'path'):
                req = args[0]
            elif not req:
                # Fallback: try to import Request type and check if first arg matches
                try:
                    from flask import Request
                    if args and isinstance(args[0], Request):
                        req = args[0]
                except (ImportError, TypeError):
                    # It's okay if Request can't be imported or args[0] isn't a Request instance;
                    # just proceed without setting req.
                    pass

            if not req:
                # No request object found, log warning and proceed without correlation
                logger.warning("No request object found for correlation tracking")
                return func(*args, **kwargs)

            # Get or generate correlation ID
            correlation_id = get_correlation_id(req)

            # Store in request object for easy access
            req.correlation_id = correlation_id
            req.start_time = time.time()

            # Log request start
            logger.info(
                "Request started",
                correlation_id=correlation_id,
                method=req.method,
                path=req.path,
                user_agent=req.headers.get('User-Agent', ''),
                remote_addr=req.headers.get('X-Forwarded-For', '').split(',')[0] if req.headers.get('X-Forwarded-For') else ''
            )

            try:
                # Execute the handler
                # For Flask, don't pass request as it's in context
                # For Cloud Functions, request is already in args[0]
                result = func(*args, **kwargs)

                # Calculate duration
                duration_ms = (time.time() - req.start_time) * 1000

                # Extract status code from result
                status_code = 200
                if isinstance(result, tuple):
                    status_code = result[1] if len(result) > 1 else 200

                # Log request completion
                logger.info(
                    "Request completed",
                    correlation_id=correlation_id,
                    method=req.method,
                    path=req.path,
                    status_code=status_code,
                    duration_ms=round(duration_ms, 2)
                )

                # Add correlation ID to response headers if result is a tuple
                if isinstance(result, tuple) and len(result) >= 2:
                    response_data, status = result[0], result[1]
                    headers = result[2] if len(result) > 2 else {}

                    # Ensure headers dict exists and add correlation ID
                    if not isinstance(headers, dict):
                        headers = {}
                    headers['X-Correlation-ID'] = correlation_id

                    return response_data, status, headers
                elif isinstance(result, tuple):
                    # If only (data, status), add headers
                    return result[0], result[1], {'X-Correlation-ID': correlation_id}
                else:
                    # If just data, wrap it
                    return result, 200, {'X-Correlation-ID': correlation_id}

            except Exception as e:
                # Log error
                duration_ms = (time.time() - req.start_time) * 1000
                logger.error(
                    "Request failed",
                    error=e,
                    correlation_id=correlation_id,
                    method=req.method,
                    path=req.path,
                    duration_ms=round(duration_ms, 2)
                )
                raise

        return wrapper
    return decorator
