"""Structured JSON logging with secret redaction.

Aligned with the logging policy: structured fields, redaction of secrets, and
no sensitive values in log output.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone

# Patterns that should never appear in logs. We redact by key name and by
# known token shapes (api keys, bearer tokens, etc.).
_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|secret|token|password|authorization|access[_-]?token)",
    re.IGNORECASE,
)
_TOKEN_SHAPE_RE = re.compile(r"\b([A-Za-z0-9_\-]{24,})\b")

_REDACTED = "***REDACTED***"


def _redact(text: str) -> str:
    # Redact long opaque tokens defensively; keep short words intact.
    return _TOKEN_SHAPE_RE.sub(
        lambda m: _REDACTED if _looks_secret(m.group(1)) else m.group(1), text
    )


def _looks_secret(token: str) -> bool:
    # Heuristic: mixed alphanumeric with no spaces and length >= 24.
    return len(token) >= 24 and any(c.isdigit() for c in token)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": _redact(record.getMessage()),
        }
        # Attach structured extras (anything not standard on LogRecord).
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS or key.startswith("_"):
                continue
            if _SECRET_KEY_RE.search(key):
                payload[key] = _REDACTED
            else:
                payload[key] = _safe(value)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _safe(value):
    try:
        json.dumps(value, default=str)
        return value
    except Exception:  # noqa: BLE001
        return str(value)


_STANDARD_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime"}


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    # Quiet noisy third-party loggers.
    for noisy in ("uvicorn.access", "apscheduler", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
