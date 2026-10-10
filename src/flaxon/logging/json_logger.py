from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any


class JSONLogger:
    """Write structured JSON records with bound fields and exception information."""

    def __init__(self, name: str = "flaxon", level: int = logging.INFO) -> None:
        self.name = name
        self.level = level
        self._logger = logging.getLogger(name)
        self._configure()
        self._context: dict[str, Any] = {}

    def _configure(self) -> None:
        self._logger.setLevel(self.level)

        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": logging.getLevelName(level),
            "logger": self.name,
            "message": message,
            **self._context,
            **kwargs,
        }

        if kwargs.get("exc_info"):
            log_data["exception"] = traceback.format_exc()

        self._logger.log(level, json.dumps(log_data, default=str, ensure_ascii=False))

    def debug(self, message: str, **kwargs: Any) -> None:
        """Write a DEBUG record with the supplied fields or formatting arguments."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Write an INFO record with the supplied fields or formatting arguments."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Write a WARNING record with the supplied fields or formatting arguments."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Write an ERROR record with the supplied fields or formatting arguments."""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Write a CRITICAL record with the supplied fields or formatting arguments."""
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Write an ERROR record including the active exception information."""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)

    def bind(self, **kwargs: Any) -> JSONLogger:
        """Bind additional fields and return a context-aware logger or context facade."""
        new_logger = JSONLogger(self.name, self.level)
        new_logger._context = {**self._context, **kwargs}
        return new_logger

    def with_context(self, **kwargs: Any) -> JSONLogger:
        """Return a logger with additional bound context fields."""
        return self.bind(**kwargs)

    def set_level(self, level: int | str) -> None:
        """Set the minimum log level using an integer or a level name."""
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
        self.level = level
        self._logger.setLevel(level)

    def add_field(self, key: str, value: Any) -> None:
        """Set a persistent field on this structured logger."""
        self._context[key] = value

    def remove_field(self, key: str) -> None:
        """Remove a persistent field from this structured logger."""
        self._context.pop(key, None)

    def clear_context(self) -> None:
        """Clear persistent fields on this structured logger."""
        self._context.clear()


_default_json_logger = JSONLogger()


def get_json_logger(name: str = "flaxon") -> JSONLogger:
    """Create a structured JSON logger with the requested name."""
    return JSONLogger(name)
