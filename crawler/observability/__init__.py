"""Observability components for logging, metrics, and tracing."""

from crawler.observability.logger import (
    LogContext,
    configure_logging,
    get_logger,
)
from crawler.observability.metrics import (
    MetricsCollector,
    configure_metrics,
    get_metrics_collector,
)
from crawler.observability.tracing import (
    TracingConfig,
    add_span_attributes,
    add_span_event,
    configure_tracing,
    get_tracer,
    trace_api_call,
    trace_llm_call,
    trace_operation,
    trace_span,
    trace_sync_operation,
)

__all__ = [
    "LogContext",
    "configure_logging",
    "get_logger",
    "MetricsCollector",
    "configure_metrics",
    "get_metrics_collector",
    "TracingConfig",
    "configure_tracing",
    "get_tracer",
    "trace_operation",
    "trace_span",
    "trace_sync_operation",
    "trace_llm_call",
    "trace_api_call",
    "add_span_attributes",
    "add_span_event",
]
