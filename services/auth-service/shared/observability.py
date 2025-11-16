"""Cloud-agnostic logging and tracing with OpenTelemetry."""
import os
import logging
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from functools import wraps

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

class StructuredLogger:
    """Cloud-agnostic structured logger with JSON output."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """Configure structured JSON logger."""
        logger = logging.getLogger(self.service_name)
        logger.setLevel(logging.INFO)
        logger.handlers = []

        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

        return logger

    def _get_trace_context(self):
        """Get current trace context from OpenTelemetry."""
        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            return {
                "trace_id": format(span_context.trace_id, '032x'),
                "span_id": format(span_context.span_id, '016x')
            }
        return {}

    def _build_log_entry(self, message: str, level: str, correlation_id: Optional[str] = None, **extra) -> Dict[str, Any]:
        """Build structured log entry with trace context."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": level,
            "service": self.service_name,
            "message": message,
        }

        # Auto-add trace context
        trace_context = self._get_trace_context()
        if trace_context:
            entry.update(trace_context)

        if correlation_id:
            entry["correlation_id"] = correlation_id

        entry.update(extra)
        return entry

    def info(self, message: str, **kwargs):
        """Log INFO level."""
        entry = self._build_log_entry(message, "INFO", **kwargs)
        self.logger.info(json.dumps(entry))

    def warning(self, message: str, **kwargs):
        """Log WARNING level."""
        entry = self._build_log_entry(message, "WARNING", **kwargs)
        self.logger.warning(json.dumps(entry))

    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log ERROR level with exception details."""
        if error:
            import traceback
            kwargs["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "stacktrace": traceback.format_exc()
            }
        entry = self._build_log_entry(message, "ERROR", **kwargs)
        self.logger.error(json.dumps(entry))

    def debug(self, message: str, **kwargs):
        """Log DEBUG level."""
        entry = self._build_log_entry(message, "DEBUG", **kwargs)
        self.logger.debug(json.dumps(entry))


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        """Format log record as JSON if not already formatted."""
        if isinstance(record.msg, str) and record.msg.startswith('{'):
            return record.msg

        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "message": record.getMessage(),
        }
        return json.dumps(log_obj)


class TracingManager:
    """OpenTelemetry tracing manager."""

    def __init__(self, service_name: str, environment: str = "production"):
        self.service_name = service_name
        self.environment = environment
        self.tracer = self._setup_tracer()

    def _setup_tracer(self):
        """Setup OpenTelemetry tracer with Google Cloud Trace exporter."""
        resource = Resource.create({
            "service.name": self.service_name,
            "service.namespace": "discord-bot",
            "deployment.environment": self.environment,
        })

        tracer_provider = TracerProvider(resource=resource)

        # Setup Cloud Trace exporter (disabled in local dev)
        if not os.getenv("LOCAL_DEV"):
            try:
                project_id = os.getenv('GCP_PROJECT_ID')
                cloud_trace_exporter = CloudTraceSpanExporter(project_id=project_id)
                span_processor = BatchSpanProcessor(cloud_trace_exporter)
                tracer_provider.add_span_processor(span_processor)
            except Exception as e:
                print(f"Warning: Could not setup Cloud Trace exporter: {e}")

        trace.set_tracer_provider(tracer_provider)
        return trace.get_tracer(self.service_name)

    def get_tracer(self):
        """Get the configured tracer."""
        return self.tracer

    def instrument_flask(self, app):
        """Auto-instrument Flask application."""
        try:
            FlaskInstrumentor().instrument_app(app)
        except Exception as e:
            print(f"Warning: Could not instrument Flask: {e}")

    def instrument_requests(self):
        """Auto-instrument requests library."""
        try:
            RequestsInstrumentor().instrument()
        except Exception as e:
            print(f"Warning: Could not instrument requests: {e}")


def init_observability(service_name: str, app=None, environment: str = None):
    """Initialize logging and tracing for a service.

    Args:
        service_name: Name of the service
        app: Flask app instance (optional)
        environment: Environment name (auto-detected from env vars)

    Returns:
        tuple: (logger, tracing_manager)
    """
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'production')

    logger = StructuredLogger(service_name)
    tracing = TracingManager(service_name, environment)

    if app:
        tracing.instrument_flask(app)

    tracing.instrument_requests()

    logger.info("Observability initialized", service=service_name, environment=environment)

    return logger, tracing


def traced_function(operation_name: Optional[str] = None):
    """Decorator to trace a function with OpenTelemetry.

    Usage:
        @traced_function("my_operation")
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            op_name = operation_name or func.__name__

            with tracer.start_as_current_span(op_name) as span:
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("function.status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("function.status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper
    return decorator


def get_correlation_id(request=None) -> str:
    """Get or generate correlation ID from request.

    Checks for correlation ID in:
    1. X-Correlation-ID header
    2. X-Request-ID header
    3. Generates new UUID if not found
    """
    if request:
        return (
            request.headers.get('X-Correlation-ID') or
            request.headers.get('X-Request-ID') or
            str(uuid.uuid4())
        )
    return str(uuid.uuid4())


def propagate_correlation_headers(correlation_id: str) -> Dict[str, str]:
    """Generate headers to propagate correlation ID to downstream services.

    Returns:
        dict: Headers to include in downstream requests
    """
    return {
        'X-Correlation-ID': correlation_id,
        'X-Request-ID': correlation_id,
    }

