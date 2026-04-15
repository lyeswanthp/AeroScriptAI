"""Structured JSON logging configuration with request ID correlation."""

import logging
import json
import sys
import uuid
from contextvars import ContextVar
from contextlib import contextmanager
from typing import Optional

# Context variable for request-scoped request ID
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    return request_id_var.get()


@contextmanager
def request_context(request_id: Optional[str] = None):
    """Set a request ID for the duration of a request context."""
    token = request_id_var.set(request_id or str(uuid.uuid4()))
    try:
        yield
    finally:
        request_id_var.reset(token)


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON with request ID correlation."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        req_id = get_request_id()
        if req_id:
            log_entry["request_id"] = req_id

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure root logger with JSON formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add JSON handler for stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
