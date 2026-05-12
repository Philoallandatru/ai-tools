"""Unit tests for structured logging."""

import json
import logging
from io import StringIO

import pytest

from crawler.observability import LogContext, configure_logging, get_logger


class TestStructuredLogging:
    """Test structured logging functionality."""

    def test_json_logging(self):
        """Test JSON format logging."""
        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        # Configure logger
        logger = get_logger("test.json")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        from crawler.observability.logger import JSONFormatter
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        # Log a message
        logger.info("Test message")

        # Parse JSON output
        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["logger"] == "test.json"
        assert "timestamp" in log_data

    def test_log_context(self):
        """Test LogContext adds context to logs."""
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        logger = get_logger("test.context")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        from crawler.observability.logger import ContextFilter, JSONFormatter
        handler.setFormatter(JSONFormatter())
        handler.addFilter(ContextFilter())
        logger.addHandler(handler)

        # Log with context
        with LogContext(operation="test_op", user="test_user"):
            logger.info("Message with context")

        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        assert "context" in log_data
        assert log_data["context"]["operation"] == "test_op"
        assert log_data["context"]["user"] == "test_user"

    def test_nested_context(self):
        """Test nested LogContext merges correctly."""
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        logger = get_logger("test.nested")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        from crawler.observability.logger import ContextFilter, JSONFormatter
        handler.setFormatter(JSONFormatter())
        handler.addFilter(ContextFilter())
        logger.addHandler(handler)

        # Nested contexts
        with LogContext(operation="outer"):
            with LogContext(step="inner"):
                logger.info("Nested message")

        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        assert log_data["context"]["operation"] == "outer"
        assert log_data["context"]["step"] == "inner"

    def test_context_cleanup(self):
        """Test context is cleaned up after exiting."""
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        logger = get_logger("test.cleanup")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        from crawler.observability.logger import ContextFilter, JSONFormatter
        handler.setFormatter(JSONFormatter())
        handler.addFilter(ContextFilter())
        logger.addHandler(handler)

        # Use context
        with LogContext(temp="value"):
            pass

        # Log after context exit
        logger.info("After context")

        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        # Context should not be present
        assert "context" not in log_data or log_data.get("context") == {}

    def test_configure_logging_json(self):
        """Test configure_logging with JSON format."""
        configure_logging(level="DEBUG", format_type="json")

        # Check root logger level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_logging_text(self):
        """Test configure_logging with text format."""
        configure_logging(level="WARNING", format_type="text")

        # Check root logger level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_extra_fields(self):
        """Test logging with extra fields."""
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        logger = get_logger("test.extra")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        from crawler.observability.logger import JSONFormatter
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        # Log with extra fields
        logger.info("Message", extra={"extra_fields": {"count": 42, "status": "ok"}})

        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        assert "extra_fields" in log_data
        assert log_data["extra_fields"]["count"] == 42
        assert log_data["extra_fields"]["status"] == "ok"
