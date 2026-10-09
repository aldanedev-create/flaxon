from __future__ import annotations

import contextvars
from typing import Any


class LogContext:
    """Read and update the active context without mutating inherited dictionaries."""

    _context: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
        "log_context", default=None
    )

    @property
    def _data(self) -> dict[str, Any]:
        return self._context.get() or {}

    def set(self, key: str, value: Any) -> None:
        """Set a field in the active log context using copy-on-write storage."""
        data = dict(self._data)
        data[key] = value
        self._context.set(data)

    def get(self, key: str, default: Any = None) -> Any:
        """Read a field from the active log context or return its fallback."""
        return self._data.get(key, default)

    def update(self, data: dict[str, Any]) -> None:
        """Merge fields into a fresh dictionary for the active log context."""
        merged = dict(self._data)
        merged.update(data)
        self._context.set(merged)

    def remove(self, key: str) -> None:
        """Remove a field without modifying another context's dictionary."""
        data = dict(self._data)
        data.pop(key, None)
        self._context.set(data)

    def clear(self) -> None:
        """Replace the active log context with an empty dictionary."""
        self._context.set({})

    def get_all(self) -> dict[str, Any]:
        """Return a shallow copy of the active log fields."""
        return dict(self._data)

    def __enter__(self) -> LogContext:
        self._token = self._context.set(dict(self._data))
        return self

    def __exit__(self, *args: Any) -> None:
        if hasattr(self, "_token"):
            self._context.reset(self._token)

    def bind(self, **kwargs: Any) -> LogContext:
        """Bind additional fields in the active context and return a context facade."""
        new_context = LogContext()
        new_context.update(self._data)
        new_context.update(kwargs)
        return new_context


_default_context = LogContext()


def set_log_context(key: str, value: Any) -> None:
    """Set a field in the active log context."""
    _default_context.set(key, value)


def get_log_context(key: str, default: Any = None) -> Any:
    """Read a field from the active log context or return its fallback."""
    return _default_context.get(key, default)


def update_log_context(data: dict[str, Any]) -> None:
    """Merge fields into the active log context."""
    _default_context.update(data)


def clear_log_context() -> None:
    """Clear fields from the active log context."""
    _default_context.clear()


class LogContextMiddleware:
    """Bind a request ID for an HTTP call and restore the previous context."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Bind HTTP request fields for this call and restore the outer context."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request_id = scope.get("flaxon.request_id", "unknown")
        with LogContext():
            set_log_context("request_id", request_id)
            await self.app(scope, receive, send)
