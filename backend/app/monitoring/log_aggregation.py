"""
Structured logging with PII masking and context propagation
"""

import logging
import re
from datetime import datetime

from app.monitoring.tracing import get_span_id, get_trace_id
from pythonjsonlogger import jsonlogger


class StructuredLogger:
    """Structured JSON logger with context"""

    # PII patterns to mask
    PII_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "api_key": r'(api[_-]?key|apikey|access[_-]?token)[\s:=]+["\']?([a-zA-Z0-9_-]+)["\']?',
    }

    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))

        # JSON formatter
        formatter = jsonlogger.JsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s %(trace_id)s %(span_id)s"
        )

        # Console handler
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _mask_pii(self, message: str) -> str:
        """Mask PII in log messages"""
        for pattern_name, pattern in self.PII_PATTERNS.items():
            message = re.sub(pattern, f"[{pattern_name.upper()}_REDACTED]", message)
        return message

    def _add_context(self, extra: dict | None = None) -> dict:
        """Add trace context to logs"""
        context = {
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": get_trace_id(),
            "span_id": get_span_id(),
        }
        if extra:
            context.update(extra)
        return context

    def info(self, message: str, **kwargs):
        message = self._mask_pii(message)
        self.logger.info(message, extra=self._add_context(kwargs))

    def warning(self, message: str, **kwargs):
        message = self._mask_pii(message)
        self.logger.warning(message, extra=self._add_context(kwargs))

    def error(self, message: str, **kwargs):
        message = self._mask_pii(message)
        self.logger.error(message, extra=self._add_context(kwargs))

    def critical(self, message: str, **kwargs):
        message = self._mask_pii(message)
        self.logger.critical(message, extra=self._add_context(kwargs))


# Create loggers for different components
app_logger = StructuredLogger("app")
api_logger = StructuredLogger("api")
db_logger = StructuredLogger("database")
aws_logger = StructuredLogger("aws")
