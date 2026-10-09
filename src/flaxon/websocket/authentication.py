"""WebSocket authentication for Flaxon.

This module provides authentication support for WebSocket connections.
"""

from __future__ import annotations

import base64
import functools
import hashlib
import hmac
import json
import time
import urllib.parse
import uuid
from collections.abc import Callable
from typing import Any

from flaxon.exceptions import Unauthorized

from .connection import WebSocket


class WebSocketAuth:
    """WebSocket authentication.

    This class provides authentication for WebSocket connections.

    Example:
        ```python
        auth = WebSocketAuth(secret_key="your-secret")


        @app.websocket("/ws/chat")
        @auth.require_auth
        async def chat(socket: WebSocket):
            user = socket.user
            await socket.accept()
            ...
        ```
    """

    def __init__(self, secret_key: str, token_header: str = "authorization") -> None:
        """Initialize the WebSocket authentication.

        Args:
            secret_key: The secret key for token validation.
            token_header: The header name for the token.
        """
        self.secret_key = secret_key.encode()
        self.token_header = token_header.lower().encode("latin-1")

    def require_auth(self, func: Callable) -> Callable:
        """Decorator to require authentication for a WebSocket endpoint.

        Args:
            func: The WebSocket endpoint function.

        Returns:
            The wrapped function.
        """

        @functools.wraps(func)
        async def wrapper(socket: WebSocket, *args: Any, **kwargs: Any) -> Any:
            user = await self.authenticate(socket)
            socket.user = user
            return await func(socket, *args, **kwargs)

        return wrapper

    async def authenticate(self, socket: WebSocket) -> Any:
        """Authenticate a WebSocket connection.

        Args:
            socket: The WebSocket connection.

        Returns:
            The authenticated user.

        Raises:
            Unauthorized: If authentication fails.
        """
        token = self._extract_token(socket)
        if not token:
            raise Unauthorized("Missing authentication token")

        user = await self._validate_token(token)
        if not user:
            raise Unauthorized("Invalid authentication token")

        return user

    def _extract_token(self, socket: WebSocket) -> str | None:
        """Extract token from headers or query parameters."""
        if hasattr(socket, "scope"):
            scope = socket.scope
            headers = scope.get("headers", [])

            for key, value in headers:
                if key.lower() == self.token_header:
                    auth = value.decode("latin-1")
                    if auth.startswith("Bearer "):
                        return auth[7:]
                    return auth

            query_string = scope.get("query_string", b"").decode("utf-8")
            if query_string:
                params = urllib.parse.parse_qs(query_string)
                if "token" in params:
                    return params["token"][0]

        return None

    async def _validate_token(self, token: str) -> Any:
        """Validate a token.

        Args:
            token: The token to validate.

        Returns:
            The user object or None if invalid.
        """
        try:
            parts = token.split(".", 2)
            if len(parts) != 3:
                return None

            header, payload, signature = parts

            expected = self._sign(f"{header}.{payload}")
            if not hmac.compare_digest(expected, signature):
                return None

            user = json.loads(base64.urlsafe_b64decode(payload + "=="))
            return user

        except (ValueError, UnicodeDecodeError):
            return None

    def _sign(self, data: str) -> str:
        """Sign data with HMAC."""
        return hmac.new(self.secret_key, data.encode(), hashlib.sha256).hexdigest()

    def create_token(self, user: dict[str, Any], expires_in: int = 86400) -> str:
        """Create a token for a user.

        Args:
            user: The user data.
            expires_in: The expiration time in seconds.

        Returns:
            The token string.
        """
        header = (
            base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        )
        payload = (
            base64
            .urlsafe_b64encode(
                json.dumps({
                    **user,
                    "iat": int(time.time()),
                    "exp": int(time.time()) + expires_in,
                    "jti": uuid.uuid4().hex[:16],
                }).encode()
            )
            .decode()
            .rstrip("=")
        )

        signature = self._sign(f"{header}.{payload}")
        return f"{header}.{payload}.{signature}"


class WebSocketAuthMiddleware:
    """WebSocket authentication middleware.

    This middleware adds authentication to WebSocket connections.

    Example:
        ```python
        app.add_middleware(
            WebSocketAuthMiddleware,
            secret_key="your-secret",
            require_auth=True,
        )
        ```
    """

    def __init__(
        self,
        app: Any,
        secret_key: str,
        require_auth: bool = True,
        token_header: str = "authorization",
    ) -> None:
        """Initialize the WebSocket authentication middleware.

        Args:
            app: The ASGI application.
            secret_key: The secret key for token validation.
            require_auth: Whether to require authentication for all connections.
            token_header: The header name for the token.
        """
        self.app = app
        self.auth = WebSocketAuth(secret_key, token_header)
        self.require_auth = require_auth

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Process the request with authentication."""
        if scope.get("type") != "websocket":
            await self.app(scope, receive, send)
            return

        if not self.require_auth:
            await self.app(scope, receive, send)
            return

        socket = WebSocket(scope, receive, send)

        try:
            user = await self.auth.authenticate(socket)
            socket.user = user
            scope["user"] = user
        except Unauthorized as exc:
            await socket.close(code=4001, reason=str(exc.detail))
            return

        await self.app(scope, receive, send)
