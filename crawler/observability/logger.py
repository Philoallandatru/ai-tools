"""
Structured logging with JSON format and context management.

This module provides:
- JSON-formatted logs for machine parsing
- Context managers for adding structured fields
- Configurable log levels and outputs
- Thread-safe context storage
"""

import json
import logging
import sys
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Thread-local context storage
_log_context: ContextVar[Dict[str, Any]] = ContextVar("log_context", default={})


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context from ContextVar
        context = _log_context.get()
        if context:
            log_data["context"] = context

        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_data["extra_fields"] = record.extra_fields

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class ContextFilter(logging.Filter):
    """Add context information to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to the record."""
        context = _log_context.get()
        if context:
            record.context = context
        return True


class LogContext:
    """Context manager for adding structured context to logs."""

    def __init__(self, **kwargs):
        """
        Initialize log context.

        Args:
            **kwargs: Key-value pairs to add to log context
        """
        self.context = kwargs
        self.token = None
        self.previous_context = None

    def __enter__(self):
        """Enter context and merge with existing context."""
        self.previous_context = _log_context.get().copy()
        new_context = {**self.previous_context, **self.context}
        self.token = _log_context.set(new_context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore previous context."""
        if self.token:
            _log_context.set(self.previous_context)


def configure_logging(
    level: str = "INFO",
    format_type: str = "json",
    output_file: Optional[str] = None,
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ('json' or 'text')
        output_file: Optional file path for log output
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create formatter
    if format_type == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(ContextFilter())
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if output_file:
        file_handler = logging.FileHandler(output_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(ContextFilter())
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class StructuredLogger:
    """Wrapper for logging with structured fields."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def debug(self, message: str, **extra_fields):
        """Log debug message with extra fields."""
        self._log(logging.DEBUG, message, extra_fields)

    def info(self, message: str, **extra_fields):
        """Log info message with extra fields."""
        self._log(logging.INFO, message, extra_fields)

    def warning(self, message: str, **extra_fields):
        """Log warning message with extra fields."""
        self._log(logging.WARNING, message, extra_fields)

    def error(self, message: str, **extra_fields):
        """Log error message with extra fields."""
        self._log(logging.ERROR, message, extra_fields)

    def critical(self, message: str, **extra_fields):
        """Log critical message with extra fields."""
        self._log(logging.CRITICAL, message, extra_fields)

    def _log(self, level: int, message: str, extra_fields: Dict[str, Any]):
        """Internal logging method."""
        extra = {"extra_fields": extra_fields} if extra_fields else {}
        self.logger.log(level, message, extra=extra)


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(get_logger(name))
