"""
Request context management.

This module provides context management for requests, including
request-local storage and context variables.
"""

from __future__ import annotations

import contextvars
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from flaxon.http import Request
from flaxon.websocket import WebSocket

_request_context: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "flaxon_request_context",
    default=None,
)

_request: contextvars.ContextVar[Request | None] = contextvars.ContextVar(
    "flaxon_request",
    default=None,
)

_websocket: contextvars.ContextVar[WebSocket | None] = contextvars.ContextVar(
    "flaxon_websocket",
    default=None,
)


class RequestContext:
    """Request context manager for request-local data."""

    @property
    def _data(self) -> dict[str, Any]:
        return _request_context.get() or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the context."""
        data = dict(self._data)
        data[key] = value
        _request_context.set(data)

    def delete(self, key: str) -> None:
        """Delete a value from the context."""
        data = dict(self._data)
        data.pop(key, None)
        _request_context.set(data)

    def clear(self) -> None:
        """Clear all values from the context."""
        _request_context.set({})

    def keys(self) -> list[str]:
        """Get all keys in the context."""
        return list(self._data.keys())

    def items(self) -> list[tuple[str, Any]]:
        """Get all items in the context."""
        return list(self._data.items())

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the context."""
        return key in self._data

    def __getitem__(self, key: str) -> Any:
        """Get a value from the context."""
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a value in the context."""
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        """Delete a value from the context."""
        self.delete(key)


@contextmanager
def request_context(request: Request) -> Generator[RequestContext, None, None]:
    """Context manager for request-local data."""
    token1 = _request.set(request)
    token2 = _request_context.set({})
    try:
        yield RequestContext()
    finally:
        _request.reset(token1)
        _request_context.reset(token2)


@contextmanager
def websocket_context(socket: WebSocket) -> Generator[RequestContext, None, None]:
    """Context manager for WebSocket-local data."""
    token1 = _websocket.set(socket)
    token2 = _request_context.set({})
    try:
        yield RequestContext()
    finally:
        _websocket.reset(token1)
        _request_context.reset(token2)


def get_current_request() -> Request | None:
    """Get the current request from context."""
    return _request.get()


def get_current_websocket() -> WebSocket | None:
    """Get the current WebSocket from context."""
    return _websocket.get()


def get_request_context() -> RequestContext:
    """Get the current request context."""
    return RequestContext()


class ContextMiddleware:
    """Middleware that sets up request context."""

    def __init__(self, app: Any) -> None:
        """Initialize the middleware."""
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the request with context."""
        if scope.get("type") == "http":
            request = Request(scope, receive, None)
            with request_context(request):
                await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)
