from __future__ import annotations

import json
import logging
from datetime import datetime


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
            import traceback

            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": "".join(traceback.format_exception(*record.exc_info)),
            }

        if hasattr(record, "extra"):
            if isinstance(record.extra, dict):
                log_data.update(record.extra)

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
            "user_agent": getattr(record, "user_agent", "-"),
            "request_id": getattr(record, "request_id", "-"),
        }

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
            "user_id": getattr(record, "user_id", "-"),
            "resource": getattr(record, "resource", "-"),
            "changes": getattr(record, "changes", {}),
            "ip": getattr(record, "ip", "-"),
            "user_agent": getattr(record, "user_agent", "-"),
        }

        return json.dumps(log_data, default=str, ensure_ascii=False)
