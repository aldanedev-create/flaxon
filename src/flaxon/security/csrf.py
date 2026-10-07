from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Any

from flaxon.exceptions import Forbidden
from flaxon.http import Request


class CSRF:
    def __init__(self, secret_key: str, cookie_name: str = "_csrf", header_name: str = "x-csrf-token") -> None:
        self.secret_key = secret_key.encode()
        self.cookie_name = cookie_name
        self.header_name = header_name.lower()

    def _sign(self, data: str) -> str:
        return hmac.new(self.secret_key, data.encode(), hashlib.sha256).hexdigest()

    def generate_token(self) -> str:
        nonce = secrets.token_urlsafe(32)
        timestamp = str(int(time.time()))
        signature = self._sign(f"{nonce}.{timestamp}")
        return f"{nonce}.{timestamp}.{signature}"

    def verify_token(self, token: str) -> bool:
        try:
            nonce, timestamp_str, signature = token.split(".", 2)
            timestamp = int(timestamp_str)
            age = time.time() - timestamp
            if not nonce or age < 0 or age > 3600:
                return False
            expected = self._sign(f"{nonce}.{timestamp_str}")
            return hmac.compare_digest(expected, signature)
        except ValueError:
            return False

    def get_token_from_request(self, request: Request) -> str | None:
        token = request.headers.get(self.header_name)
        if token:
            return token
        # Cookies are sent automatically by browsers, including on forged
        # requests. Require explicit submission rather than trusting a cookie.
        return None

    def validate_request(self, request: Request) -> None:
        if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
            return

        token = self.get_token_from_request(request)
        if token is None:
            raise Forbidden("CSRF token missing")

        if not self.verify_token(token):
            raise Forbidden("CSRF token invalid")


class CSRFMiddleware:
    def __init__(self, app: Any, secret_key: str, cookie_name: str = "_csrf", header_name: str = "x-csrf-token") -> None:
        self.app = app
        self.csrf = CSRF(secret_key, cookie_name, header_name)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        from flaxon.http import Request
        request = Request(scope, receive, None)

        try:
            self.csrf.validate_request(request)
        except Forbidden:
            async def send_error(message: dict[str, Any]) -> None:
                await send(message)

            response_headers = [
                (b"content-type", b"application/json"),
            ]
            await send({
                "type": "http.response.start",
                "status": 403,
                "headers": response_headers,
            })
            await send({
                "type": "http.response.body",
                "body": b'{"success":false,"error":{"code":"FX-CSRF-001","message":"CSRF validation failed"}}',
                "more_body": False,
            })
            return

        await self.app(scope, receive, send)
