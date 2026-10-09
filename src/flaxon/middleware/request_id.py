"""Request correlation ID middleware."""

from __future__ import annotations

import secrets
from typing import Any

from .base import Middleware


class RequestIDMiddleware(Middleware):
    """Assign a stable request identifier and expose it in responses."""

    def __init__(self, app: Any, header_name: str = "x-request-id") -> None:
        super().__init__(app)
        self.header_name = header_name.lower().encode("latin-1")

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        request_id = next(
            (
                value.decode("latin-1")
                for key, value in scope.get("headers", [])
                if key.lower() == self.header_name
            ),
            secrets.token_hex(8),
        )
        scope["request_id"] = request_id

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((self.header_name, request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
