"""Response security header middleware."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import Middleware


class SecurityHeadersMiddleware(Middleware):
    """Add secure browser defaults to HTTP responses."""

    DEFAULT_HEADERS: ClassVar[Any] = {"x-content-type-options": "nosniff", "x-frame-options": "DENY"}

    def __init__(self, app: Any, headers: dict[str, str] | None = None) -> None:
        super().__init__(app)
        self.headers = {**self.DEFAULT_HEADERS, **(headers or {})}

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.extend(
                    (key.encode("latin-1"), value.encode("latin-1")) for key, value in self.headers.items()
                )
                message["headers"] = response_headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
