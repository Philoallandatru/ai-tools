"""Prometheus-compatible metrics collection for observability.

This module provides a MetricsCollector class that tracks:
- Sync operations (requests, duration, errors)
- LLM usage (requests, tokens, response time)
- System metrics (active operations, cache size)

Metrics are exposed via HTTP endpoint for Prometheus scraping.
"""

import time
from contextlib import contextmanager
from functools import wraps
from threading import Lock
from typing import Any, Callable, Dict, Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Gauge = Histogram = None
    start_http_server = None

from crawler.observability import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Collect and expose Prometheus metrics."""

    def __init__(self, enabled: bool = True, port: int = 9090):
        """
        Initialize metrics collector.

        Args:
            enabled: Whether to collect metrics
            port: HTTP port for metrics endpoint
        """
        self.enabled = enabled and PROMETHEUS_AVAILABLE
        self.port = port
        self._server_started = False
        self._lock = Lock()

        if not PROMETHEUS_AVAILABLE:
            logger.warning(
                "prometheus_client not installed. Metrics collection disabled. "
                "Install with: pip install prometheus-client"
            )
            self.enabled = False
            return

        if not enabled:
            logger.info("Metrics collection disabled")
            return

        # Counter metrics
        self.sync_requests_total = Counter(
            "sync_requests_total",
            "Total number of sync requests",
            ["source_type", "source_name", "status"],
        )

        self.llm_requests_total = Counter(
            "llm_requests_total",
            "Total number of LLM requests",
            ["provider", "model", "status"],
        )

        self.llm_tokens_total = Counter(
            "llm_tokens_total",
            "Total number of LLM tokens used",
            ["provider", "model", "token_type"],
        )

        # Histogram metrics
        self.sync_duration_seconds = Histogram(
            "sync_duration_seconds",
            "Duration of sync operations in seconds",
            ["source_type", "source_name"],
            buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
        )

        self.llm_response_time_seconds = Histogram(
            "llm_response_time_seconds",
            "LLM response time in seconds",
            ["provider", "model"],
            buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120),
        )

        # Gauge metrics
        self.active_syncs = Gauge(
            "active_syncs",
            "Number of active sync operations",
            ["source_type"],
        )

        self.cache_size_bytes = Gauge(
            "cache_size_bytes",
            "Size of cache in bytes",
            ["cache_type"],
        )

        logger.info("Metrics collector initialized", extra={"port": port})

    def start_server(self) -> None:
        """Start HTTP server to expose metrics."""
        if not self.enabled:
            return

        with self._lock:
            if self._server_started:
                logger.warning("Metrics server already started")
                return

            try:
                start_http_server(self.port)
                self._server_started = True
                logger.info(
                    f"Metrics server started on http://localhost:{self.port}/metrics"
                )
            except OSError as e:
                logger.error(f"Failed to start metrics server: {e}")
                raise

    def track_sync(
        self, source_type: str, source_name: str
    ) -> Callable[[Callable], Callable]:
        """
        Decorator to track sync operation metrics.

        Args:
            source_type: Type of source (confluence/jira)
            source_name: Name of the source

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                if not self.enabled:
                    return func(*args, **kwargs)

                # Increment active syncs
                self.active_syncs.labels(source_type=source_type).inc()

                start_time = time.time()
                status = "success"

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "error"
                    raise
                finally:
                    # Record duration
                    duration = time.time() - start_time
                    self.sync_duration_seconds.labels(
                        source_type=source_type, source_name=source_name
                    ).observe(duration)

                    # Increment request counter
                    self.sync_requests_total.labels(
                        source_type=source_type, source_name=source_name, status=status
                    ).inc()

                    # Decrement active syncs
                    self.active_syncs.labels(source_type=source_type).dec()

                    logger.debug(
                        f"Sync metrics recorded",
                        extra={
                            "source_type": source_type,
                            "source_name": source_name,
                            "duration": duration,
                            "status": status,
                        },
                    )

            return wrapper

        return decorator

    def track_llm(
        self, provider: str, model: str
    ) -> Callable[[Callable], Callable]:
        """
        Decorator to track LLM request metrics.

        Args:
            provider: LLM provider name
            model: Model name

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                if not self.enabled:
                    return func(*args, **kwargs)

                start_time = time.time()
                status = "success"

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "error"
                    raise
                finally:
                    # Record response time
                    duration = time.time() - start_time
                    self.llm_response_time_seconds.labels(
                        provider=provider, model=model
                    ).observe(duration)

                    # Increment request counter
                    self.llm_requests_total.labels(
                        provider=provider, model=model, status=status
                    ).inc()

                    logger.debug(
                        f"LLM metrics recorded",
                        extra={
                            "provider": provider,
                            "model": model,
                            "duration": duration,
                            "status": status,
                        },
                    )

            return wrapper

        return decorator

    @contextmanager
    def track_active_sync(self, source_type: str):
        """
        Context manager to track active sync operations.

        Args:
            source_type: Type of source (confluence/jira)
        """
        if self.enabled:
            self.active_syncs.labels(source_type=source_type).inc()
        try:
            yield
        finally:
            if self.enabled:
                self.active_syncs.labels(source_type=source_type).dec()

    def record_llm_tokens(
        self, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> None:
        """
        Record LLM token usage.

        Args:
            provider: LLM provider name
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
        """
        if not self.enabled:
            return

        self.llm_tokens_total.labels(
            provider=provider, model=model, token_type="prompt"
        ).inc(prompt_tokens)

        self.llm_tokens_total.labels(
            provider=provider, model=model, token_type="completion"
        ).inc(completion_tokens)

        logger.debug(
            f"LLM tokens recorded",
            extra={
                "provider": provider,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        )

    def update_cache_size(self, cache_type: str, size_bytes: int) -> None:
        """
        Update cache size metric.

        Args:
            cache_type: Type of cache
            size_bytes: Size in bytes
        """
        if not self.enabled:
            return

        self.cache_size_bytes.labels(cache_type=cache_type).set(size_bytes)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(enabled=False)
    return _metrics_collector


def configure_metrics(enabled: bool = True, port: int = 9090) -> MetricsCollector:
    """
    Configure the global metrics collector.

    Args:
        enabled: Whether to enable metrics collection
        port: HTTP port for metrics endpoint

    Returns:
        Configured MetricsCollector instance
    """
    global _metrics_collector
    _metrics_collector = MetricsCollector(enabled=enabled, port=port)
    return _metrics_collector
