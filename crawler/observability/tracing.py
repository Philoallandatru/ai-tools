"""OpenTelemetry distributed tracing for observability.

This module provides tracing capabilities for tracking operations across
the application, including:
- Sync operations
- LLM calls
- External API requests
- Data processing pipelines

Traces can be exported to Jaeger, Zipkin, or other OTLP-compatible backends.
"""

import functools
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.trace import Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    trace = None
    OTLPSpanExporter = None
    Resource = None
    TracerProvider = None
    BatchSpanProcessor = None
    ConsoleSpanExporter = None
    Status = StatusCode = None

from crawler.observability import get_logger

logger = get_logger(__name__)


class TracingConfig:
    """Configuration for OpenTelemetry tracing."""

    def __init__(
        self,
        enabled: bool = True,
        service_name: str = "crawler",
        otlp_endpoint: Optional[str] = None,
        console_export: bool = False,
    ):
        """
        Initialize tracing configuration.

        Args:
            enabled: Whether to enable tracing
            service_name: Name of the service for trace identification
            otlp_endpoint: OTLP endpoint URL (e.g., "http://localhost:4317")
            console_export: Whether to export traces to console (for debugging)
        """
        self.enabled = enabled
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint
        self.console_export = console_export


_tracer_provider: Optional[Any] = None
_tracer: Optional[Any] = None


def configure_tracing(config: TracingConfig) -> Optional[Any]:
    """
    Configure OpenTelemetry tracing.

    Args:
        config: Tracing configuration

    Returns:
        Configured tracer instance, or None if OpenTelemetry not available
    """
    global _tracer_provider, _tracer

    if not OPENTELEMETRY_AVAILABLE:
        logger.warning(
            "OpenTelemetry not installed. Tracing disabled. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc"
        )
        return None

    if not config.enabled:
        logger.info("Tracing disabled")
        _tracer = trace.get_tracer(__name__)
        return _tracer

    # Create resource with service name
    resource = Resource.create({"service.name": config.service_name})

    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)

    # Add OTLP exporter if endpoint provided
    if config.otlp_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=config.otlp_endpoint)
            _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(
                f"OTLP trace exporter configured",
                extra={"endpoint": config.otlp_endpoint},
            )
        except Exception as e:
            logger.error(f"Failed to configure OTLP exporter: {e}")

    # Add console exporter for debugging
    if config.console_export:
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("Console trace exporter configured")

    # Set as global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    # Get tracer
    _tracer = trace.get_tracer(__name__)

    logger.info(
        "Tracing configured",
        extra={"service_name": config.service_name, "enabled": config.enabled},
    )

    return _tracer


def get_tracer() -> Optional[Any]:
    """Get the configured tracer instance, or None if tracing not available."""
    global _tracer
    if not OPENTELEMETRY_AVAILABLE:
        return None
    if _tracer is None:
        _tracer = trace.get_tracer(__name__)
    return _tracer


def trace_operation(
    operation_name: str, attributes: Optional[Dict[str, Any]] = None
) -> Callable[[Callable], Callable]:
    """
    Decorator to trace an operation.

    Args:
        operation_name: Name of the operation for the span
        attributes: Optional attributes to add to the span

    Returns:
        Decorator function

    Example:
        @trace_operation("sync_confluence_space", {"source": "test"})
        def sync_space(space_key: str):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not OPENTELEMETRY_AVAILABLE:
                # If OpenTelemetry not available, just call the function
                return func(*args, **kwargs)

            tracer = get_tracer()
            if tracer is None:
                return func(*args, **kwargs)

            with tracer.start_as_current_span(operation_name) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))

                # Add function info
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


@contextmanager
def trace_span(
    span_name: str, attributes: Optional[Dict[str, Any]] = None, record_exception: bool = True
):
    """
    Context manager to create a trace span.

    Args:
        span_name: Name of the span
        attributes: Optional attributes to add to the span
        record_exception: Whether to record exceptions in the span

    Example:
        with trace_span("process_page", {"page_id": "123"}):
            process_page(page_id)
    """
    if not OPENTELEMETRY_AVAILABLE:
        # If OpenTelemetry not available, just yield without tracing
        yield
        return

    tracer = get_tracer()
    if tracer is None:
        yield
        return

    with tracer.start_as_current_span(span_name) as span:
        # Add attributes
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            if record_exception:
                span.record_exception(e)
            raise


def add_span_attributes(attributes: Dict[str, Any]) -> None:
    """
    Add attributes to the current span.

    Args:
        attributes: Attributes to add

    Example:
        add_span_attributes({"pages_processed": 10, "errors": 0})
    """
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, str(value))


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Add an event to the current span.

    Args:
        name: Event name
        attributes: Optional event attributes

    Example:
        add_span_event("page_downloaded", {"page_id": "123", "size": 1024})
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.add_event(name, attributes=attributes or {})


def trace_sync_operation(source_type: str, source_name: str) -> Callable[[Callable], Callable]:
    """
    Decorator specifically for tracing sync operations.

    Args:
        source_type: Type of source (confluence/jira)
        source_name: Name of the source

    Returns:
        Decorator function
    """
    return trace_operation(
        f"sync.{source_type}",
        attributes={"source.type": source_type, "source.name": source_name},
    )


def trace_llm_call(provider: str, model: str) -> Callable[[Callable], Callable]:
    """
    Decorator specifically for tracing LLM calls.

    Args:
        provider: LLM provider name
        model: Model name

    Returns:
        Decorator function
    """
    return trace_operation(
        "llm.generate",
        attributes={"llm.provider": provider, "llm.model": model},
    )


def trace_api_call(service: str, endpoint: str) -> Callable[[Callable], Callable]:
    """
    Decorator specifically for tracing external API calls.

    Args:
        service: Service name (e.g., "confluence", "jira")
        endpoint: API endpoint

    Returns:
        Decorator function
    """
    return trace_operation(
        f"api.{service}",
        attributes={"api.service": service, "api.endpoint": endpoint},
    )
