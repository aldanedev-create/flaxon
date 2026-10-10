"""
Logging middleware for Flaxon.

This module provides middleware for logging requests and responses.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .base import Middleware


class LoggingMiddleware(Middleware):
    """Logging middleware."""

    def __init__(
        self,
        app: Any,
        logger: logging.Logger | None = None,
        log_headers: bool = False,
        log_body: bool = False,
        log_level: int = logging.INFO,
    ) -> None:
        super().__init__(app)
        self.logger = logger or logging.getLogger("flaxon.http")
        self.log_headers = log_headers
        self.log_body = log_body
        self.log_level = log_level

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        request_id = scope.get("flaxon.request_id", "unknown")
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        status_code = 500

        self._log_request(scope, request_id)

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                if self.log_headers:
                    headers = message.get("headers", [])
                    self.logger.log(
                        self.log_level,
                        "Response headers: %s",
                        {k.decode(): v.decode() for k, v in headers},
                        extra={"request_id": request_id},
                    )
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            self.logger.error(
                "Error processing request: %s",
                str(exc),
                exc_info=True,
                extra={"request_id": request_id},
            )
            raise
        finally:
            elapsed = (time.perf_counter() - start_time) * 1000
            self.logger.log(
                self.log_level,
                "%s %s %s %d %dms",
                method,
                path,
                request_id,
                status_code,
                int(elapsed),
                extra={"request_id": request_id},
            )

    def _log_request(self, scope: dict[str, Any], request_id: str) -> None:
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        client = scope.get("client")

        client_info = f"{client[0]}:{client[1]}" if client else "unknown"

        self.logger.log(
            self.log_level,
            "Request: %s %s from %s (%s)",
            method,
            path,
            client_info,
            request_id,
            extra={"request_id": request_id},
        )

        if self.log_headers:
            headers = scope.get("headers", [])
            self.logger.log(
                self.log_level,
                "Request headers: %s",
                {k.decode(): v.decode() for k, v in headers},
                extra={"request_id": request_id},
            )
