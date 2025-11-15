"""Flask middleware for request correlation and logging."""
import time
from flask import request, g


def add_correlation_middleware(app, logger):
    """Add correlation and logging middleware to Flask app.
    
    This middleware:
    - Generates or extracts correlation IDs from requests
    - Logs request start and completion with timing
    - Adds correlation ID to response headers
    - Handles unhandled exceptions with proper logging
    """
    
    @app.before_request
    def before_request():
        """Setup correlation ID and start request tracking."""
        from observability import get_correlation_id
        
        g.correlation_id = get_correlation_id(request)
        g.start_time = time.time()
        
        logger.info(
            "Request started",
            correlation_id=g.correlation_id,
            method=request.method,
            path=request.path,
            user_agent=request.headers.get('User-Agent'),
            remote_addr=request.remote_addr
        )
    
    @app.after_request
    def after_request(response):
        """Log request completion with metrics."""
        if hasattr(g, 'start_time'):
            duration_ms = (time.time() - g.start_time) * 1000
            
            logger.info(
                "Request completed",
                correlation_id=getattr(g, 'correlation_id', None),
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2)
            )
            
            if hasattr(g, 'correlation_id'):
                response.headers['X-Correlation-ID'] = g.correlation_id
        
        return response
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Log unhandled exceptions with full context."""
        logger.error(
            "Unhandled exception",
            error=error,
            correlation_id=getattr(g, 'correlation_id', None),
            method=request.method,
            path=request.path
        )
        return {'error': 'Internal server error'}, 500

