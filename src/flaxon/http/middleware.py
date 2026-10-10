"""
HTTP middleware for Flaxon.

This module provides HTTP-specific middleware for request/response processing.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from flaxon.exceptions import BadRequest
from flaxon.http import Request, Response

from .body import BodyLimiter

__all__ = [
    "BodyLimitMiddleware",
    "RequestIDMiddleware",
    "ResponseTimeMiddleware",
]


class RequestIDMiddleware:
    """Adds a unique request ID to each request."""

    def __init__(self, app: Any, header_name: str = "x-request-id") -> None:
        self.app = app
        self.header_name = header_name.lower()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex[:16]
        scope["flaxon.request_id"] = request_id

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((self.header_name.encode("latin-1"), request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


class BodyLimitMiddleware:
    """Limits the size of request bodies."""

    def __init__(self, app: Any, max_size: int = 10 * 1024 * 1024) -> None:
        self.app = app
        self.limiter = BodyLimiter(max_size)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.limiter.check(Request(scope, receive, None))
        except BadRequest as exc:
            response = Response(str(exc), status_code=413)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


class ResponseTimeMiddleware:
    """Adds response time headers and logging."""

    def __init__(self, app: Any, header_name: str = "x-response-time") -> None:
        self.app = app
        self.header_name = header_name.lower()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                elapsed = (time.perf_counter() - start_time) * 1000
                headers = list(message.get("headers", []))
                headers.append((self.header_name.encode("latin-1"), f"{elapsed:.2f}ms".encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
