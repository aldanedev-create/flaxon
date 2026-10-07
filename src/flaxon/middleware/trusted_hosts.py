"""
Trusted hosts middleware for Flaxon.

This module provides middleware for validating the Host header against allowed hosts.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from flaxon.exceptions import BadRequest

from .base import Middleware


class TrustedHostsMiddleware(Middleware):
    """
    Trusted hosts middleware.

    This middleware validates the Host header against a list of allowed hosts.

    Example:
        ```python
        app.add_middleware(
            TrustedHostsMiddleware,
            allowed_hosts=["example.com", "api.example.com"],
        )
        ```
    """

    def __init__(
        self,
        app: Any,
        allowed_hosts: list[str] | tuple[str, ...],
        *,
        require_www: bool = False,
    ) -> None:
        """
        Initialize the trusted hosts middleware.

        Args:
            app: The ASGI application.
            allowed_hosts: List of allowed hosts.
            require_www: Whether to require www subdomain.
        """
        super().__init__(app)
        self.allowed_hosts = set(allowed_hosts)
        self.require_www = require_www

    def _get_host(self, scope: dict[str, Any]) -> str | None:
        """Extract the Host header from the scope."""
        for key, value in scope.get("headers", []):
            if key.lower() == b"host":
                return value.decode("latin-1")
        return None

    def _is_allowed(self, host: str) -> bool:
        """Check if the host is allowed."""
        # ASGI supplies the Host header, which commonly includes a port in
        # development and can include one in production.
        # Host is an HTTP authority, not a URL. Reject URL delimiters and
        # whitespace before parsing so userinfo and paths cannot be hidden.
        if (
            not host
            or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in host)
            or any(char in host for char in "@/\\?#")
        ):
            return False
        try:
            authority = urlsplit(f"//{host}")
            hostname = authority.hostname
            # Accessing port also validates its syntax and range.
            _ = authority.port
        except ValueError:
            hostname = None
        if hostname is None:
            return False
        host = hostname.lower()
        if host in self.allowed_hosts:
            return True

        if self.require_www:
            if not host.startswith("www."):
                return False
            host_without_www = host[4:]
            if host_without_www in self.allowed_hosts:
                return True

        return False

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Process the request with host validation."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        host = self._get_host(scope)

        if not host:
            raise BadRequest("Missing Host header")

        if not self._is_allowed(host):
            raise BadRequest(f"Host '{host}' is not allowed")

        await self.app(scope, receive, send)
