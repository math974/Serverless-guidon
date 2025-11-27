"""Request correlation and logging utilities for Functions Framework.
"""
import time
from functools import wraps
from flask import request as flask_request
from typing import Callable

def with_correlation(logger):
    """Decorator to handle correlation ID and request logging for Flask.

    Usage:
        @with_correlation(logger)
        def my_handler(request: Request):
            # correlation_id is automatically available via request.correlation_id
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from shared.observability import get_correlation_id

            # Utilise flask.request
            req = flask_request
            correlation_id = get_correlation_id(req)
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
