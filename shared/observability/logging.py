"""
Structured logging configuration for the Multi-Agent Orchestration Platform.
Provides JSON-formatted logging with context propagation.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Optional

import structlog
from structlog.types import Processor


def add_timestamp(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Add ISO-format timestamp to log events."""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def add_service_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Add service context to log events."""
    event_dict["service"] = os.getenv("SERVICE_NAME", "unknown")
    event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
    event_dict["version"] = os.getenv("SERVICE_VERSION", "1.0.0")
    return event_dict


def add_trace_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Add OpenTelemetry trace context to log events."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            ctx = span.get_span_context()
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
    except ImportError:
        pass
    return event_dict


def configure_logging(
    service_name: str,
    log_level: str = "INFO",
    json_format: bool = True,
    add_trace: bool = True,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        service_name: Name of the service for log context
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to output logs in JSON format
        add_trace: Whether to add trace context to logs
    """
    # Set service name in environment for processors
    os.environ["SERVICE_NAME"] = service_name

    # Build processor chain
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_timestamp,
        add_service_context,
    ]

    if add_trace:
        processors.append(add_trace_context)

    processors.extend([
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ])

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    log_level_num = getattr(logging, log_level.upper(), logging.INFO)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_num)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level_num)

    if json_format:
        # Use a simple formatter for structlog-processed output
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))

    root_logger.addHandler(handler)

    # Configure third-party loggers to be less verbose
    for logger_name in ["aiokafka", "kafka", "sqlalchemy", "aiohttp", "httpx", "uvicorn"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    structlog.get_logger().info(
        "Logging configured",
        service=service_name,
        level=log_level,
        json_format=json_format,
    )


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Optional logger name. If not provided, uses the calling module name.

    Returns:
        A structured logger instance
    """
    return structlog.get_logger(name)


class LoggerAdapter:
    """
    Adapter to use structlog with libraries that expect standard logging interface.
    """

    def __init__(self, logger: structlog.BoundLogger):
        self._logger = logger

    def debug(self, msg: str, *args, **kwargs) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        self._logger.exception(msg, *args, **kwargs)


def bind_context(**kwargs: Any) -> None:
    """
    Bind context variables that will be included in all subsequent log messages.

    Usage:
        bind_context(request_id="abc123", user_id="user456")
        logger.info("Processing request")  # Will include request_id and user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """
    Unbind context variables.

    Usage:
        unbind_context("request_id", "user_id")
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


class LogContext:
    """
    Context manager for temporary log context.

    Usage:
        with LogContext(request_id="abc123"):
            logger.info("Processing")  # Includes request_id
        logger.info("Done")  # Does not include request_id
    """

    def __init__(self, **kwargs: Any):
        self.context = kwargs
        self.token = None

    def __enter__(self) -> "LogContext":
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.token:
            structlog.contextvars.reset_contextvars(self.token)
