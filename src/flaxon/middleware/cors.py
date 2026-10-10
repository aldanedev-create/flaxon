"""Cross-origin resource sharing middleware."""

from __future__ import annotations

from typing import Any

from .base import Middleware


class CORSMiddleware(Middleware):
    """Apply CORS headers and handle preflight requests."""

    def __init__(
        self,
        app: Any,
        allowed_origins: list[str] | None = None,
        allow_credentials: bool = False,
        allow_methods: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
        if allow_credentials and "*" in self.allowed_origins:
            raise ValueError("allow_credentials=True requires explicit allowed_origins")
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        origin = next(
            (value.decode("latin-1") for key, value in scope.get("headers", []) if key.lower() == b"origin"),
            None,
        )
        response_origin = origin or (
            self.allowed_origins[0] if self.allowed_origins and self.allowed_origins[0] != "*" else "*"
        )
        permitted = origin is None or "*" in self.allowed_origins or origin in self.allowed_origins
        if scope.get("type") == "http" and scope.get("method") == "OPTIONS":
            headers: list[tuple[bytes, bytes]] = []
            if permitted and origin is not None:
                headers.extend([
                    (b"access-control-allow-origin", response_origin.encode("latin-1")),
                    (b"access-control-allow-methods", ", ".join(self.allow_methods).encode("latin-1")),
                ])
                if "*" not in self.allowed_origins:
                    headers.append((b"vary", b"origin"))
                if self.allow_credentials:
                    headers.append((b"access-control-allow-credentials", b"true"))
            await send({"type": "http.response.start", "status": 204, "headers": headers})
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return

        async def send_wrapper(message: dict[str, Any]) -> None:
            if permitted and message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"access-control-allow-origin", response_origin.encode("latin-1")))
                if origin is not None and "*" not in self.allowed_origins:
                    existing_vary = next((value for key, value in headers if key.lower() == b"vary"), b"")
                    vary_values = {
                        item.strip().lower() for item in existing_vary.decode("latin-1").split(",") if item
                    }
                    if "origin" not in vary_values:
                        headers = [(key, value) for key, value in headers if key.lower() != b"vary"]
                        vary_values.add("origin")
                        headers.append((b"vary", ", ".join(sorted(vary_values)).encode("latin-1")))
                if self.allow_credentials:
                    headers.append((b"access-control-allow-credentials", b"true"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
