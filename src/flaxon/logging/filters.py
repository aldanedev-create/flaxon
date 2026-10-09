from __future__ import annotations

import logging
import re


class Filter:
    """A named log filter that allows records unless overridden."""

    def __init__(self, name: str) -> None:
        self.name = name

    def filter(self, record: logging.LogRecord) -> bool:
        """Allow the record; subclasses override this method to restrict records."""
        return True


class LevelFilter(Filter):
    """Allow records within configured minimum and maximum log levels."""

    def __init__(self, name: str, min_level: int, max_level: int | None = None) -> None:
        super().__init__(name)
        self.min_level = min_level
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        """Return whether this record satisfies the configured filter criteria."""
        if record.levelno < self.min_level:
            return False
        if self.max_level is not None and record.levelno > self.max_level:
            return False
        return True


class RequestFilter(Filter):
    """Filter available request path and method fields on log records."""

    def __init__(self, name: str, path_pattern: str | None = None, method: str | None = None) -> None:
        super().__init__(name)
        self.path_pattern = re.compile(path_pattern) if path_pattern else None
        self.method = method.upper() if method else None

    def filter(self, record: logging.LogRecord) -> bool:
        """Return whether this record satisfies the configured filter criteria."""
        path = getattr(record, "path", None)
        method = getattr(record, "method", None)

        if self.path_pattern and path:
            if not self.path_pattern.search(path):
                return False

        if self.method and method:
            if method.upper() != self.method:
                return False

        return True


class ModuleFilter(Filter):
    """Allow records from selected module names."""

    def __init__(self, name: str, modules: list[str]) -> None:
        super().__init__(name)
        self.modules = modules

    def filter(self, record: logging.LogRecord) -> bool:
        """Return whether this record satisfies the configured filter criteria."""
        return record.module in self.modules


class ExcludeModuleFilter(Filter):
    """Reject records from selected module names."""

    def __init__(self, name: str, modules: list[str]) -> None:
        super().__init__(name)
        self.modules = modules

    def filter(self, record: logging.LogRecord) -> bool:
        """Return whether this record satisfies the configured filter criteria."""
        return record.module not in self.modules


class UserFilter(Filter):
    """Allow records whose user ID matches a configured user."""

    def __init__(self, name: str, user_ids: list[str | int]) -> None:
        super().__init__(name)
        self.user_ids = {str(uid) for uid in user_ids}

    def filter(self, record: logging.LogRecord) -> bool:
        """Return whether this record satisfies the configured filter criteria."""
        user_id = getattr(record, "user_id", None)
        if user_id is None:
            return False
        return str(user_id) in self.user_ids


class RequestIDFilter(Filter):
    """Allow records belonging to a selected request ID."""

    def __init__(self, name: str, request_id: str) -> None:
        super().__init__(name)
        self.request_id = request_id

    def filter(self, record: logging.LogRecord) -> bool:
        """Return whether this record satisfies the configured filter criteria."""
        rid = getattr(record, "request_id", None)
        return rid == self.request_id


class StatusFilter(Filter):
    """Allow records with one of the configured HTTP statuses."""

    def __init__(self, name: str, statuses: list[int]) -> None:
        super().__init__(name)
        self.statuses = set(statuses)

    def filter(self, record: logging.LogRecord) -> bool:
        """Return whether this record satisfies the configured filter criteria."""
        status = getattr(record, "status", None)
        return status in self.statuses


def add_filter(logger: logging.Logger, filter_obj: Filter) -> None:
    """Attach a Flaxon filter to a standard logger."""
    logger.addFilter(filter_obj)


def remove_filter(logger: logging.Logger, filter_obj: Filter) -> None:
    """Remove a Flaxon filter from a standard logger."""
    logger.removeFilter(filter_obj)
