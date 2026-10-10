"""
Protocol definitions for Flaxon.

This module defines protocols (interfaces) that components must implement
to be used with the framework.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from .typing import JSONValue, ReceiveType, ScopeType, SendType

# ============================================================
# ASGI Protocol
# ============================================================


@runtime_checkable
class ASGIApplication(Protocol):
    """Protocol for ASGI applications."""

    async def __call__(self, scope: ScopeType, receive: ReceiveType, send: SendType) -> None:
        """Handle the supplied call using this object's configured behavior."""
        ...


# ============================================================
# Middleware Protocol
# ============================================================


@runtime_checkable
class Middleware(Protocol):
    """Protocol for middleware components."""

    def __init__(self, app: ASGIApplication, **options: Any) -> None:
        """Perform the   init   operation for middleware."""
        ...

    async def __call__(self, scope: ScopeType, receive: ReceiveType, send: SendType) -> None:
        """Handle the supplied call using this object's configured behavior."""
        ...


# ============================================================
# Router Protocol
# ============================================================


@runtime_checkable
class RouterProtocol(Protocol):
    """Protocol for routers."""

    def route(self, path: str, **kwargs: Any) -> Any:
        """Register an endpoint at the supplied path."""
        ...

    def get(self, path: str, **kwargs: Any) -> Any:
        """Retrieve the requested value using this object's configured behavior."""
        ...

    def post(self, path: str, **kwargs: Any) -> Any:
        """Register or issue an HTTP POST operation."""
        ...

    def put(self, path: str, **kwargs: Any) -> Any:
        """Register or issue an HTTP PUT operation."""
        ...

    def patch(self, path: str, **kwargs: Any) -> Any:
        """Register or issue an HTTP PATCH operation."""
        ...

    def delete(self, path: str, **kwargs: Any) -> Any:
        """Delete the specified entry from the configured store."""
        ...

    def websocket(self, path: str, **kwargs: Any) -> Any:
        """Register a WebSocket endpoint at the supplied path."""
        ...

    def include_router(self, router: RouterProtocol, prefix: str | None = None) -> None:
        """Perform the include router operation for router protocol."""
        ...

    def match(self, path: str, method: str) -> Any:
        """Perform the match operation for router protocol."""
        ...

    def match_websocket(self, path: str) -> Any:
        """Perform the match websocket operation for router protocol."""
        ...

    def url_for(self, name: str, **params: Any) -> str:
        """Build a URL from a named route and its parameters."""
        ...


# ============================================================
# Request Protocol
# ============================================================


@runtime_checkable
class RequestProtocol(Protocol):
    """Protocol for HTTP requests."""

    method: str
    path: str
    headers: dict[str, str]
    path_params: dict[str, Any]
    query: dict[str, Any]
    cookies: dict[str, str]
    client: tuple[str, int] | None

    async def body(self) -> bytes:
        """Perform the body operation for request protocol."""
        ...

    async def json(self) -> JSONValue:
        """Decode or expose the JSON representation of the current value."""
        ...

    async def text(self) -> str:
        """Perform the text operation for request protocol."""
        ...

    async def render(self, template_name: str, context: dict[str, Any] | None = None) -> Any:
        """Render the requested content using the supplied context."""
        ...


# ============================================================
# Response Protocol
# ============================================================


@runtime_checkable
class ResponseProtocol(Protocol):
    """Protocol for HTTP responses."""

    status_code: int
    headers: dict[str, str]
    body: bytes

    async def __call__(self, scope: ScopeType, receive: ReceiveType, send: SendType) -> None:
        """Handle the supplied call using this object's configured behavior."""
        ...

    @classmethod
    def from_value(cls, value: Any) -> ResponseProtocol:
        """Construct from the value."""
        ...


# ============================================================
# WebSocket Protocol
# ============================================================


@runtime_checkable
class WebSocketProtocol(Protocol):
    """Protocol for WebSocket connections."""

    path_params: dict[str, Any]
    accepted: bool
    closed: bool

    async def accept(self, subprotocol: str | None = None) -> None:
        """Accept the incoming WebSocket connection."""
        ...

    async def receive_text(self) -> str:
        """Receive the text."""
        ...

    async def receive_json(self) -> JSONValue:
        """Receive the json."""
        ...

    async def send_text(self, value: str) -> None:
        """Send the text."""
        ...

    async def send_json(self, value: Any) -> None:
        """Send the json."""
        ...

    async def close(self, code: int = 1000) -> None:
        """Release the resources held by this object."""
        ...

    async def join(self, room: str) -> None:
        """Add the connection to the named room."""
        ...

    async def leave(self, room: str) -> None:
        """Remove the connection from the named room."""
        ...

    async def broadcast_json(self, room: str, value: Any) -> None:
        """Perform the broadcast json operation for web socket protocol."""
        ...

    def iter_json(self) -> AsyncIterator[JSONValue]:
        """Perform the iter json operation for web socket protocol."""
        ...


# ============================================================
# Validator Protocol
# ============================================================


@runtime_checkable
class ValidatorProtocol(Protocol):
    """Protocol for validation schemas."""

    __fields__: dict[str, Any]

    @classmethod
    def load(cls, data: dict[str, Any]) -> ValidatorProtocol:
        """Load the requested resource using the configured source."""
        ...

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        ...


# ============================================================
# Cache Protocol
# ============================================================


@runtime_checkable
class CacheProtocol(Protocol):
    """Protocol for cache backends."""

    async def get(self, key: str) -> Any:
        """Retrieve the requested value using this object's configured behavior."""
        ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store the supplied value under its key."""
        ...

    async def delete(self, key: str) -> None:
        """Delete the specified entry from the configured store."""
        ...

    async def clear(self) -> None:
        """Remove the stored entries."""
        ...

    async def exists(self, key: str) -> bool:
        """Return whether the requested entry exists."""
        ...


# ============================================================
# Session Protocol
# ============================================================


@runtime_checkable
class SessionProtocol(Protocol):
    """Protocol for session backends."""

    async def get(self, session_id: str, key: str) -> Any:
        """Retrieve the requested value using this object's configured behavior."""
        ...

    async def set(self, session_id: str, key: str, value: Any) -> None:
        """Store the supplied value under its key."""
        ...

    async def delete(self, session_id: str, key: str) -> None:
        """Delete the specified entry from the configured store."""
        ...

    async def clear(self, session_id: str) -> None:
        """Remove the stored entries."""
        ...

    async def exists(self, session_id: str) -> bool:
        """Return whether the requested entry exists."""
        ...


# ============================================================
# Plugin Protocol
# ============================================================


@runtime_checkable
class PluginProtocol(Protocol):
    """Protocol for plugins."""

    name: str
    version: str

    def setup(self, app: ASGIApplication) -> None:
        """Configure the supplied application or resource."""
        ...

    def startup(self) -> None:
        """Perform the startup operation for plugin protocol."""
        ...

    def shutdown(self) -> None:
        """Perform the shutdown operation for plugin protocol."""
        ...


# ============================================================
# Health Check Protocol
# ============================================================


@runtime_checkable
class HealthCheckProtocol(Protocol):
    """Protocol for health checks."""

    async def check(self) -> dict[str, Any]:
        """Perform the check operation for health check protocol."""
        ...


# ============================================================
# Task Protocol
# ============================================================


@runtime_checkable
class TaskProtocol(Protocol):
    """Protocol for background tasks."""

    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the configured operation."""
        ...


# ============================================================
# Export
# ============================================================

__all__ = [
    "ASGIApplication",
    "CacheProtocol",
    "HealthCheckProtocol",
    "Middleware",
    "PluginProtocol",
    "RequestProtocol",
    "ResponseProtocol",
    "RouterProtocol",
    "SessionProtocol",
    "TaskProtocol",
    "ValidatorProtocol",
    "WebSocketProtocol",
]
