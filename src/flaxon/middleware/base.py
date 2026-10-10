"""Base ASGI middleware class."""

from __future__ import annotations

from typing import Any


class Middleware:
    """Base class for middleware that delegates to an ASGI application."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        await self.app(scope, receive, send)
