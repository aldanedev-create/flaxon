"""
Body limit middleware for Flaxon.

This module provides middleware for limiting request body sizes.
"""

from __future__ import annotations

from typing import Any

from flaxon.exceptions import PayloadTooLarge

from .base import Middleware


class BodyLimitMiddleware(Middleware):
    """Body limit middleware."""

    def __init__(self, app: Any, max_size: int = 10 * 1024 * 1024) -> None:
        super().__init__(app)
        self.max_size = max_size

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        content_length = None
        for key, value in scope.get("headers", []):
            if key.lower() == b"content-length":
                try:
                    content_length = int(value.decode("latin-1"))
                except ValueError:
                    pass
                break

        if content_length is not None and content_length > self.max_size:
            raise PayloadTooLarge(max_size=self.max_size)

        # Content-Length is only an early rejection hint. Always count bytes
        # received, including when a proxy or client understates the length.
        body_size = 0

        async def receive_wrapper() -> dict[str, Any]:
            nonlocal body_size
            message = await receive()

            if message["type"] == "http.request":
                body = message.get("body", b"")
                body_size += len(body)
                if body_size > self.max_size:
                    raise PayloadTooLarge(max_size=self.max_size)

            return message

        await self.app(scope, receive_wrapper, send)
