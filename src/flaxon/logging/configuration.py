from __future__ import annotations

import logging
import os
from typing import Any, ClassVar


class LoggingConfig:
    """Configure logging from independent handler definitions and environment values."""

    DEFAULTS: ClassVar[dict[str, Any]] = {
        "level": logging.INFO,
        "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S",
        "propagate": False,
        "handlers": [],
    }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = {**self.DEFAULTS, **(config or {})}
        self._config["handlers"] = [dict(handler) for handler in self._config["handlers"]]
        self._load_env()

    def _load_env(self) -> None:
        log_level = os.environ.get("LOG_LEVEL", "").upper()
        if log_level:
            level = getattr(logging, log_level, None)
            if level is not None:
                self._config["level"] = level

        log_format = os.environ.get("LOG_FORMAT")
        if log_format:
            self._config["format"] = log_format

        log_file = os.environ.get("LOG_FILE")
        if log_file:
            self._config["handlers"].append({
                "type": "rotating_file",
                "filename": log_file,
            })

    @property
    def level(self) -> int:
        """Read or update the configured minimum log level."""
        return self._config["level"]

    @level.setter
    def level(self, value: int) -> None:
        """Read or update the configured minimum log level."""
        self._config["level"] = value

    @property
    def format(self) -> str:
        """Return the log record format string."""
        return self._config["format"]

    @property
    def datefmt(self) -> str:
        """Return the timestamp format string."""
        return self._config["datefmt"]

    @property
    def propagate(self) -> bool:
        """Return whether records propagate to ancestor loggers."""
        return self._config["propagate"]

    @property
    def handlers(self) -> list[dict[str, Any]]:
        """Return this configuration's independent handler definitions."""
        return self._config["handlers"]

    def add_handler(self, handler: dict[str, Any]) -> None:
        """Append a handler definition to this configuration."""
        self._config["handlers"].append(handler)

    def add_console_handler(self, level: int | None = None, formatter: str = "console") -> None:
        """Add a stream handler definition with optional level and formatter."""
        handler = {"type": "console", "formatter": formatter}
        if level is not None:
            handler["level"] = level
        self._config["handlers"].append(handler)

    def add_file_handler(self, filename: str, level: int | None = None, formatter: str = "console") -> None:
        """Add a file handler definition with optional level and formatter."""
        handler = {"type": "file", "filename": filename, "formatter": formatter}
        if level is not None:
            handler["level"] = level
        self._config["handlers"].append(handler)

    def add_rotating_file_handler(
        self,
        filename: str,
        max_bytes: int = 10485760,
        backup_count: int = 5,
        level: int | None = None,
        formatter: str = "console",
    ) -> None:
        """Add a file handler definition with size and backup limits."""
        handler = {
            "type": "rotating_file",
            "filename": filename,
            "max_bytes": max_bytes,
            "backup_count": backup_count,
            "formatter": formatter,
        }
        if level is not None:
            handler["level"] = level
        self._config["handlers"].append(handler)

    def to_dict(self) -> dict[str, Any]:
        """Return a shallow dictionary copy of the logging configuration."""
        return dict(self._config)
