from __future__ import annotations

from typing import Any

from flaxon.middleware import CORSMiddleware as BaseCORSMiddleware


class CORSMiddleware(BaseCORSMiddleware):
    """Corsmiddleware implementation for the security subsystem."""

    def __init__(
        self,
        app: Any,
        *,
        allowed_origins: list[str] | tuple[str, ...] = ("*",),
        allowed_methods: list[str] | tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
        allowed_headers: list[str] | tuple[str, ...] = ("*",),
        exposed_headers: list[str] | tuple[str, ...] = (),
        allow_credentials: bool = False,
        max_age: int = 600,
        allow_private_network: bool = False,
    ) -> None:
        super().__init__(
            app,
            allowed_origins=list(allowed_origins),
            allow_methods=list(allowed_methods),
            allow_credentials=allow_credentials,
        )
        self.allowed_methods = ", ".join(allowed_methods)
        self.allowed_headers = ", ".join(allowed_headers)
        self.exposed_headers = ", ".join(exposed_headers)
        self.max_age = max_age
        self.allow_private_network = allow_private_network

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        origin = self._origin(scope)
        allowed_origin = self._allowed_origin(origin)

        if scope.get("method") == "OPTIONS" and origin:
            headers = self._build_preflight_headers(allowed_origin)
            headers.append((b"vary", b"Origin"))
            await send({"type": "http.response.start", "status": 204, "headers": headers})
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start" and allowed_origin:
                headers = list(message.get("headers", []))
                headers.append((b"access-control-allow-origin", allowed_origin.encode("latin-1")))
                if self.allow_credentials:
                    headers.append((b"access-control-allow-credentials", b"true"))
                if self.exposed_headers:
                    existing = False
                    for key, _ in headers:
                        if key.lower() == b"access-control-expose-headers":
                            existing = True
                            break
                    if not existing:
                        headers.append((
                            b"access-control-expose-headers",
                            self.exposed_headers.encode("latin-1"),
                        ))
                headers.append((b"vary", b"Origin"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _build_preflight_headers(self, allowed_origin: str | None) -> list[tuple[bytes, bytes]]:
        headers = [
            (b"content-length", b"0"),
            (b"access-control-allow-methods", self.allowed_methods.encode("latin-1")),
            (b"access-control-allow-headers", self.allowed_headers.encode("latin-1")),
            (b"access-control-max-age", str(self.max_age).encode("latin-1")),
        ]
        if allowed_origin:
            headers.append((b"access-control-allow-origin", allowed_origin.encode("latin-1")))
        if self.allow_credentials:
            headers.append((b"access-control-allow-credentials", b"true"))
        if self.allow_private_network:
            headers.append((b"access-control-allow-private-network", b"true"))
        return headers

    def _origin(self, scope: dict[str, Any]) -> str | None:
        for key, value in scope.get("headers", []):
            if key.lower() == b"origin":
                return value.decode("latin-1")
        return None

    def _allowed_origin(self, origin: str | None) -> str | None:
        if origin is None:
            return None
        if "*" in self.allowed_origins and not self.allow_credentials:
            return "*"
        if origin in self.allowed_origins:
            return origin
        return None
