"""Session-bound Admin CSRF tokens with per-request context and stable signing keys."""

from __future__ import annotations

import hashlib
import secrets
from contextvars import ContextVar
from typing import Any

from flaxon.http import JSONResponse, Request
from flaxon.security.csrf import CSRF

_binding: ContextVar[str | None] = ContextVar("flaxon_admin_csrf_binding", default=None)


class AdminCSRF(CSRF):
    """Admin csrf implementation for the admin subsystem."""

    def _sign(self, data: str) -> str:
        binding = _binding.get()
        return super()._sign(f"{binding}:{data}" if binding is not None else data)

    def verify_token(self, token: str) -> bool:
        """Verify the token."""
        if _binding.get() is None:
            return False
        return super().verify_token(token)


class AdminCSRFMiddleware:
    """Admin csrfmiddleware implementation for the admin subsystem."""

    def __init__(self, app: Any, dashboard: Any) -> None:
        self.app = app
        self.dashboard = dashboard
        self.cookie_name = (
            f"flaxon_admin_csrf_{hashlib.sha256(dashboard.url_prefix.encode()).hexdigest()[:8]}"
        )

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        prefix = self.dashboard.url_prefix
        path = scope.get("path", "")
        if scope.get("type") != "http" or not (path == prefix or path.startswith(prefix + "/")):
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive, self.dashboard.app)
        nonce = request.cookies.get(self.cookie_name) or secrets.token_urlsafe(32)
        session = request.cookies.get("session_id", "")
        binding = hashlib.sha256(f"{nonce}:{session}".encode()).hexdigest()
        token = _binding.set(binding)
        try:
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                origin = request.headers.get("origin")
                host = request.headers.get("host", "")
                same_origin = f"{scope.get('scheme', 'http')}://{host}"
                trusted = self.dashboard.app.config.get("CSRF_TRUSTED_ORIGINS", [])
                if origin and origin != same_origin and origin not in trusted:
                    await JSONResponse({"error": "Untrusted Admin request origin"}, status_code=403)(
                        scope, receive, send
                    )
                    return

            async def send_response(message):
                if message.get("type") == "http.response.start" and self.cookie_name not in request.cookies:
                    headers = list(message.get("headers", []))
                    cookie = f"{self.cookie_name}={nonce}; Path={prefix}; HttpOnly; SameSite=Lax"
                    if self.dashboard.auth.cookie_secure:
                        cookie += "; Secure"
                    headers.append((b"set-cookie", cookie.encode()))
                    message = {**message, "headers": headers}
                await send(message)

            await self.app(scope, receive, send_response)
        finally:
            _binding.reset(token)
