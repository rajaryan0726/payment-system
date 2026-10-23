import json
import logging
import re
import sys
from typing import Any, Dict

# Regex patterns for sensitive data redaction
SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)"?(?:key_secret|secret|password|api_key|token|authorization)"?\s*[:=]\s*"?[^",\s]+"?'), '[REDACTED_SECRET]'),
    (re.compile(r'\b(?:\d[ -]*?){13,16}\b'), '[REDACTED_CARD]'),  # 13-16 digit card numbers
    (re.compile(r'\b\d{3,4}\b(?=.*(?:cvv|cvc))'), '[REDACTED_CVV]'),
]


def sanitize_message(message: str) -> str:
    """Sanitizes text strings by replacing sensitive patterns."""
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON with sensitive field redaction."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_message(record.getMessage()),
        }

        # Include custom context attributes if present
        for attr in ("request_id", "client_code", "payment_id", "provider_order_id", "event_type"):
            if hasattr(record, attr):
                log_data[attr] = getattr(record, attr)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configures structured JSON logging for the application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(console_handler)

    # Set third-party loggers to reasonable levels
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return logging.getLogger("bhiv_payment_service")


logger = setup_logging()
