"""Origin validation for WebSocket connections.

Browsers do not apply the same-origin policy to WebSockets: any web page can open a WebSocket to your
server, and the browser attaches the visitor's cookies to the handshake. If your sockets authenticate
with cookies or sessions, a malicious page can use them (cross-site WebSocket hijacking). Checking the
``Origin`` header the browser sends closes that hole.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlsplit

from .connection import WebSocket

#: Close code for a policy violation. Sent before the handshake completes, so clients see HTTP 403.
POLICY_VIOLATION = 1008
_DEFAULT_PORTS = {"http": 80, "https": 443, "ws": 80, "wss": 443}


def normalize_origin(value: str) -> str | None:
    """Reduce an origin like ``HTTPS://Example.com:443/`` to ``https://example.com``. ``None`` if invalid."""
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    port = parts.port
    host = parts.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    if port is None or port == _DEFAULT_PORTS[parts.scheme]:
        return f"{parts.scheme}://{host}"
    return f"{parts.scheme}://{host}:{port}"


class WebSocketOriginMiddleware:
    """Reject WebSocket handshakes from origins you have not allowed.

    Example:
        ```python
        app.add_middleware(
            WebSocketOriginMiddleware,
            allowed_origins=["https://app.example.com"],
        )
        ```

    Args:
        app: The ASGI application.
        allowed_origins: Exact origins that may connect, for example ``"https://app.example.com"``.
            ``"*"`` allows every origin (which disables the protection; avoid it with cookie auth).
        allow_same_origin: Also allow pages served from this server's own ``Host``. On by default, so
            a site that serves its own front end needs no configuration.
        allow_missing_origin: Allow handshakes with no ``Origin`` header. Browsers always send one, so
            only non-browser clients (scripts, mobile apps, other services) omit it. Turn this off for
            an endpoint that only browsers should reach.

    Pair it with ``TrustedHostsMiddleware`` so the ``Host`` header is validated too.
    """

    def __init__(
        self,
        app: Any,
        allowed_origins: Iterable[str] = (),
        *,
        allow_same_origin: bool = True,
        allow_missing_origin: bool = True,
    ) -> None:
        self.app = app
        origins = list(allowed_origins)
        self.allow_all = "*" in origins
        self.allowed = {
            normalized for origin in origins if origin != "*" and (normalized := normalize_origin(origin))
        }
        invalid = [o for o in origins if o != "*" and normalize_origin(o) is None]
        if invalid:
            raise ValueError(f"allowed_origins must be full origins like https://example.com, got {invalid}")
        self.allow_same_origin = allow_same_origin
        self.allow_missing_origin = allow_missing_origin

    def is_allowed(self, scope: dict[str, Any]) -> bool:
        """Whether the handshake described by ``scope`` may proceed."""
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_origin = headers.get(b"origin")
        if raw_origin is None:
            return self.allow_missing_origin
        if self.allow_all:
            return True
        origin = normalize_origin(raw_origin.decode("latin-1"))
        if origin is None:
            return False  # includes the literal "null" origin sent by sandboxed pages and local files
        if origin in self.allowed:
            return True
        if self.allow_same_origin and (host := headers.get(b"host")):
            scheme = origin.split("://", 1)[0]
            return normalize_origin(f"{scheme}://{host.decode('latin-1')}") == origin
        return False

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Pass allowed handshakes through and refuse the rest."""
        if scope.get("type") != "websocket" or self.is_allowed(scope):
            await self.app(scope, receive, send)
            return
        await WebSocket(scope, receive, send).close(code=POLICY_VIOLATION, reason="Origin not allowed")
