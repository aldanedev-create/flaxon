from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime

from flaxon.debugging.redaction import Redactor

# A single shared redactor keeps secrets and PII out of every structured log sink.
_REDACTOR = Redactor()


class ConsoleFormatter(logging.Formatter):
    """Format readable console records, prefixing any available request ID."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record using this formatter's output format."""
        if hasattr(record, "request_id"):
            record.msg = f"[{record.request_id}] {record.msg}"
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """Format log records as JSON with their structured metadata."""

    def __init__(self) -> None:
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record using this formatter's output format."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id

        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": "".join(traceback.format_exception(*record.exc_info)),
            }

        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data.update(_REDACTOR.redact(record.extra))

        # Redact the message and any string identifier fields as a last line of
        # defence before the record is serialized.
        log_data["message"] = _REDACTOR.redact(log_data["message"])
        for key in ("request_id", "user_id", "session_id"):
            if key in log_data and isinstance(log_data[key], str):
                log_data[key] = _REDACTOR.redact(log_data[key])

        return json.dumps(log_data, default=str, ensure_ascii=False)


class AccessFormatter(logging.Formatter):
    """Format HTTP access records with request and response metadata."""

    def __init__(self) -> None:
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record using this formatter's output format."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "type": "access",
            "level": record.levelname,
            "method": getattr(record, "method", "-"),
            "path": getattr(record, "path", "-"),
            "status": getattr(record, "status", "-"),
            "duration_ms": getattr(record, "duration_ms", "-"),
            "client_ip": getattr(record, "client_ip", "-"),
            "user_agent": _REDACTOR.redact(getattr(record, "user_agent", "-")),
            "request_id": getattr(record, "request_id", "-"),
        }
        # Query strings often carry tokens/emails; scrub the path before emitting.
        log_data["path"] = _REDACTOR.redact(log_data["path"])

        return json.dumps(log_data, default=str, ensure_ascii=False)


class AuditFormatter(logging.Formatter):
    """Format audit records describing users and resource actions."""

    def __init__(self) -> None:
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record using this formatter's output format."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "type": "audit",
            "level": record.levelname,
            "action": getattr(record, "action", "-"),
            "user_id": _REDACTOR.redact(getattr(record, "user_id", "-")),
            "resource": getattr(record, "resource", "-"),
            # Audit payloads frequently carry form data (passwords, tokens); redact them.
            "changes": _REDACTOR.redact(getattr(record, "changes", {})),
            "ip": getattr(record, "ip", "-"),
            "user_agent": _REDACTOR.redact(getattr(record, "user_agent", "-")),
            "status": getattr(record, "status", "success"),
        }
        error = getattr(record, "error", None)
        if error:
            log_data["error"] = _REDACTOR.redact(error)
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            log_data.update(_REDACTOR.redact(extra))

        return json.dumps(log_data, default=str, ensure_ascii=False)
