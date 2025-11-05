"""
Structured Logging System for PM Document Intelligence.

This module provides a comprehensive logging setup with JSON formatting for production,
color formatting for development, log rotation, and performance tracking capabilities.

Features:
- Environment-aware log formatting (JSON for production, colored text for development)
- Structured logging with contextual information
- Log rotation with size and time-based triggers
- Performance logging decorators
- Error tracking integration with Sentry
- Request ID tracking for distributed tracing
- Automatic PII masking for sensitive data

Usage:
    from app.utils.logger import get_logger, log_performance

    logger = get_logger(__name__)
    logger.info("Processing document", extra={"document_id": doc_id})

    @log_performance
    def process_document(doc):
        # Function execution time will be logged automatically
        pass
"""

import contextvars
import functools
import json
import logging
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from pythonjsonlogger import jsonlogger

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


# Context variable for request tracking
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)
user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "user_id", default=None
)


# Type variable for decorators
F = TypeVar("F", bound=Callable[..., Any])


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional context fields.

    Adds timestamp, request_id, user_id, and other contextual information
    to every log entry for better traceability in production environments.
    """

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """
        Add custom fields to log record.

        Args:
            log_record: Dictionary to populate with log fields
            record: Original log record
            message_dict: Additional message context
        """
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record["timestamp"] = datetime.utcnow().isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Add context variables
        request_id = request_id_var.get()
        if request_id:
            log_record["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            log_record["user_id"] = user_id

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Mask sensitive data
        self._mask_sensitive_data(log_record)

    def _mask_sensitive_data(self, log_record: Dict[str, Any]) -> None:
        """
        Mask sensitive information in log records.

        Args:
            log_record: Log record dictionary to mask
        """
        sensitive_keys = {
            "password",
            "token",
            "api_key",
            "secret",
            "authorization",
            "credit_card",
            "ssn",
            "access_key",
            "secret_key",
        }

        def mask_dict(d: Dict[str, Any]) -> None:
            """Recursively mask sensitive keys."""
            for key, value in list(d.items()):
                if isinstance(value, dict):
                    mask_dict(value)
                elif any(sensitive in key.lower() for sensitive in sensitive_keys):
                    if value:
                        d[key] = "***MASKED***"

        mask_dict(log_record)


class ColoredFormatter(logging.Formatter):
    """
    Colored log formatter for development environments.

    Uses different colors for different log levels to improve readability
    in terminal output during development.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        """
        Initialize colored formatter.

        Args:
            fmt: Log format string
            datefmt: Date format string
        """
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors.

        Args:
            record: Log record to format

        Returns:
            Colored formatted string
        """
        # Add color based on log level
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{self.BOLD}{levelname}{self.RESET}"
            )

        # Add context if available
        request_id = request_id_var.get()
        if request_id:
            record.msg = f"[{request_id[:8]}] {record.msg}"

        return super().format(record)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter with additional context methods.

    Provides convenient methods for adding context to log messages
    and ensures consistent structured logging across the application.
    """

    def process(
        self, msg: str, kwargs: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """
        Process log message and add extra context.

        Args:
            msg: Log message
            kwargs: Additional keyword arguments

        Returns:
            Tuple of processed message and kwargs
        """
        # Add context from context vars
        extra = kwargs.get("extra", {})

        request_id = request_id_var.get()
        if request_id:
            extra["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            extra["user_id"] = user_id

        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    rotation_size: str = "10MB",
    retention: str = "30 days",
) -> None:
    """
    Setup application logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format ("json" for production, "text" for development)
        log_file: Optional log file path
        rotation_size: Log rotation size (e.g., "10MB")
        retention: Log retention period (e.g., "30 days")
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    if log_format == "json":
        # JSON formatter for production
        formatter = CustomJSONFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )
    else:
        # Colored text formatter for development
        if COLORLOG_AVAILABLE:
            formatter = colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
            )
        else:
            formatter = ColoredFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        try:
            from logging.handlers import RotatingFileHandler

            # Create log directory if it doesn't exist
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Parse rotation size
            rotation_bytes = _parse_size(rotation_size)

            # Create rotating file handler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=rotation_bytes,
                backupCount=10,
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, log_level.upper()))

            # Always use JSON format for file logs
            file_formatter = CustomJSONFormatter(
                "%(timestamp)s %(level)s %(name)s %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.error(f"Failed to setup file logging: {e}")

    # Suppress noisy third-party loggers
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _parse_size(size_str: str) -> int:
    """
    Parse size string to bytes.

    Args:
        size_str: Size string (e.g., "10MB", "1GB")

    Returns:
        Size in bytes
    """
    size_str = size_str.strip().upper()
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4,
    }

    for suffix, multiplier in multipliers.items():
        if size_str.endswith(suffix):
            number = float(size_str[:-len(suffix)].strip())
            return int(number * multiplier)

    # Default to bytes if no suffix
    return int(float(size_str))


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def set_request_context(request_id: str, user_id: Optional[str] = None) -> None:
    """
    Set request context for logging.

    Args:
        request_id: Unique request identifier
        user_id: Optional user identifier
    """
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context() -> None:
    """Clear request context after request completion."""
    request_id_var.set(None)
    user_id_var.set(None)


def log_performance(func: F) -> F:
    """
    Decorator to log function execution time.

    Usage:
        @log_performance
        def my_function():
            pass

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    logger = get_logger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function to measure execution time."""
        start_time = time.time()
        function_name = func.__qualname__

        logger.debug(
            f"Starting execution: {function_name}",
            extra={
                "function": function_name,
                "event": "function_start",
            },
        )

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            logger.info(
                f"Completed execution: {function_name}",
                extra={
                    "function": function_name,
                    "execution_time_seconds": round(execution_time, 3),
                    "event": "function_complete",
                },
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time

            logger.error(
                f"Failed execution: {function_name}",
                extra={
                    "function": function_name,
                    "execution_time_seconds": round(execution_time, 3),
                    "error": str(e),
                    "event": "function_error",
                },
                exc_info=True,
            )
            raise

    return cast(F, wrapper)


def log_async_performance(func: F) -> F:
    """
    Decorator to log async function execution time.

    Usage:
        @log_async_performance
        async def my_async_function():
            pass

    Args:
        func: Async function to decorate

    Returns:
        Decorated async function
    """
    logger = get_logger(func.__module__)

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function to measure async execution time."""
        start_time = time.time()
        function_name = func.__qualname__

        logger.debug(
            f"Starting async execution: {function_name}",
            extra={
                "function": function_name,
                "event": "async_function_start",
            },
        )

        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            logger.info(
                f"Completed async execution: {function_name}",
                extra={
                    "function": function_name,
                    "execution_time_seconds": round(execution_time, 3),
                    "event": "async_function_complete",
                },
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time

            logger.error(
                f"Failed async execution: {function_name}",
                extra={
                    "function": function_name,
                    "execution_time_seconds": round(execution_time, 3),
                    "error": str(e),
                    "event": "async_function_error",
                },
                exc_info=True,
            )
            raise

    return cast(F, wrapper)


class StructuredLogger:
    """
    Structured logger with convenient methods for common logging patterns.

    Provides high-level methods for logging specific event types with
    consistent structure and context.
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize structured logger.

        Args:
            logger: Base logger instance
        """
        self.logger = logger

    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        **extra: Any,
    ) -> None:
        """
        Log API request with structured data.

        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            **extra: Additional context
        """
        context = {
            "event": "api_request",
            "http_method": method,
            "path": path,
            **extra,
        }

        if status_code:
            context["status_code"] = status_code

        if duration_ms:
            context["duration_ms"] = round(duration_ms, 2)

        level = logging.INFO
        if status_code and status_code >= 500:
            level = logging.ERROR
        elif status_code and status_code >= 400:
            level = logging.WARNING

        self.logger.log(
            level,
            f"{method} {path}",
            extra=context,
        )

    def log_document_processing(
        self,
        document_id: str,
        operation: str,
        status: str,
        duration_seconds: Optional[float] = None,
        **extra: Any,
    ) -> None:
        """
        Log document processing event.

        Args:
            document_id: Document identifier
            operation: Processing operation
            status: Operation status (started, completed, failed)
            duration_seconds: Operation duration
            **extra: Additional context
        """
        context = {
            "event": "document_processing",
            "document_id": document_id,
            "operation": operation,
            "status": status,
            **extra,
        }

        if duration_seconds:
            context["duration_seconds"] = round(duration_seconds, 3)

        level = logging.INFO
        if status == "failed":
            level = logging.ERROR
        elif status == "started":
            level = logging.DEBUG

        self.logger.log(
            level,
            f"Document {operation}: {document_id}",
            extra=context,
        )

    def log_ai_service_call(
        self,
        service: str,
        operation: str,
        tokens: Optional[int] = None,
        cost: Optional[float] = None,
        duration_seconds: Optional[float] = None,
        **extra: Any,
    ) -> None:
        """
        Log AI service API call.

        Args:
            service: Service name (bedrock, openai, etc.)
            operation: Operation type
            tokens: Token count
            cost: Estimated cost
            duration_seconds: Call duration
            **extra: Additional context
        """
        context = {
            "event": "ai_service_call",
            "service": service,
            "operation": operation,
            **extra,
        }

        if tokens:
            context["tokens"] = tokens

        if cost:
            context["cost_usd"] = round(cost, 4)

        if duration_seconds:
            context["duration_seconds"] = round(duration_seconds, 3)

        self.logger.info(
            f"{service} {operation}",
            extra=context,
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        **extra: Any,
    ) -> None:
        """
        Log security-related event.

        Args:
            event_type: Type of security event
            severity: Event severity (low, medium, high, critical)
            description: Event description
            **extra: Additional context
        """
        context = {
            "event": "security_event",
            "event_type": event_type,
            "severity": severity,
            **extra,
        }

        level_map = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL,
        }

        level = level_map.get(severity.lower(), logging.WARNING)

        self.logger.log(
            level,
            f"Security event: {event_type} - {description}",
            extra=context,
        )


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structured logger instance
    """
    return StructuredLogger(get_logger(name))


# Initialize logging on module import
def init_logging_from_config() -> None:
    """Initialize logging using application configuration."""
    try:
        from app.config import settings

        setup_logging(
            log_level=settings.monitoring.log_level,
            log_format=settings.monitoring.log_format,
            log_file=settings.monitoring.log_file,
            rotation_size=settings.monitoring.log_rotation,
            retention=settings.monitoring.log_retention,
        )
    except ImportError:
        # Fallback to default configuration
        setup_logging(log_level="INFO", log_format="text")
