from __future__ import annotations

import logging
from typing import Any

from .configuration import LoggingConfig
from .context import LogContext
from .formatters import ConsoleFormatter, JSONFormatter
from .handlers import ConsoleHandler, FileHandler, RotatingFileHandler


class Logger:
    """Wrap a standard logger with Flaxon configuration and active context fields."""

    def __init__(self, name: str = "flaxon", config: LoggingConfig | None = None) -> None:
        self.name = name
        self.config = config or LoggingConfig()
        self._logger = logging.getLogger(name)
        self._context = LogContext()
        self._configure()

    def _configure(self) -> None:
        self._logger.setLevel(self.config.level)

        if self.config.handlers:
            for handler_config in self.config.handlers:
                handler = self._create_handler(handler_config)
                if handler:
                    self._logger.addHandler(handler)

        if not self._logger.handlers:
            handler = ConsoleHandler()
            formatter = ConsoleFormatter()
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

        self._logger.propagate = self.config.propagate

    def _create_handler(self, handler_config: dict[str, Any]) -> logging.Handler | None:
        handler_type = handler_config.get("type", "console")

        if handler_type == "console":
            handler = ConsoleHandler()
        elif handler_type == "file":
            handler = FileHandler(handler_config.get("filename", "flaxon.log"))
        elif handler_type == "rotating_file":
            handler = RotatingFileHandler(
                handler_config.get("filename", "flaxon.log"),
                max_bytes=handler_config.get("max_bytes", 10485760),
                backup_count=handler_config.get("backup_count", 5),
            )
        else:
            return None

        formatter_type = handler_config.get("formatter", "console")
        if formatter_type == "json":
            formatter = JSONFormatter()
        else:
            formatter = ConsoleFormatter()

        handler.setFormatter(formatter)
        handler.setLevel(handler_config.get("level", logging.INFO))
        return handler

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Write a DEBUG record with the supplied fields or formatting arguments."""
        self._log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Write an INFO record with the supplied fields or formatting arguments."""
        self._log(logging.INFO, message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Write a WARNING record with the supplied fields or formatting arguments."""
        self._log(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Write an ERROR record with the supplied fields or formatting arguments."""
        self._log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Write a CRITICAL record with the supplied fields or formatting arguments."""
        self._log(logging.CRITICAL, message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Write an ERROR record including the active exception information."""
        self._log(logging.ERROR, message, *args, exc_info=True, **kwargs)

    def _log(self, level: int, message: str, *args: Any, **kwargs: Any) -> None:
        extra = kwargs.pop("extra", {})
        context_data = self._context.get_all()
        if context_data:
            extra.update(context_data)

        if "exc_info" not in kwargs:
            kwargs["exc_info"] = None

        self._logger.log(level, message, *args, extra=extra, **kwargs)

    def bind(self, **kwargs: Any) -> Logger:
        """Bind additional fields and return a context-aware logger or context facade."""
        new_logger = Logger(self.name, self.config)
        new_logger._context.update(kwargs)
        return new_logger

    def with_context(self, **kwargs: Any) -> Logger:
        """Return a logger with additional bound context fields."""
        return self.bind(**kwargs)

    def set_level(self, level: int | str) -> None:
        """Set the minimum log level using an integer or a level name."""
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
        self._logger.setLevel(level)

    def get_logger(self) -> logging.Logger:
        """Return a standard logger or create a configured Flaxon logger."""
        return self._logger

    def __getattr__(self, name: str) -> Any:
        return getattr(self._logger, name)


_default_logger = Logger("flaxon")


def get_logger(name: str = "flaxon") -> Logger:
    """Return a standard logger or create a configured Flaxon logger."""
    return Logger(name)


def debug(message: str, *args: Any, **kwargs: Any) -> None:
    """Write a DEBUG record with the supplied fields or formatting arguments."""
    _default_logger.debug(message, *args, **kwargs)


def info(message: str, *args: Any, **kwargs: Any) -> None:
    """Write an INFO record with the supplied fields or formatting arguments."""
    _default_logger.info(message, *args, **kwargs)


def warning(message: str, *args: Any, **kwargs: Any) -> None:
    """Write a WARNING record with the supplied fields or formatting arguments."""
    _default_logger.warning(message, *args, **kwargs)


def error(message: str, *args: Any, **kwargs: Any) -> None:
    """Write an ERROR record with the supplied fields or formatting arguments."""
    _default_logger.error(message, *args, **kwargs)


def critical(message: str, *args: Any, **kwargs: Any) -> None:
    """Write a CRITICAL record with the supplied fields or formatting arguments."""
    _default_logger.critical(message, *args, **kwargs)


def exception(message: str, *args: Any, **kwargs: Any) -> None:
    """Write an ERROR record including the active exception information."""
    _default_logger.exception(message, *args, **kwargs)
