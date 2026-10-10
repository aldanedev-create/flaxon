from __future__ import annotations

import logging
import time
from typing import Any

from flaxon.http import Request

from .formatters import AccessFormatter


class AccessLogger:
    """Write HTTP response status, duration, and request metadata to a logger."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("flaxon.access")
        self._configure()

    def _configure(self) -> None:
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = AccessFormatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    def log_request(
        self,
        request: Request,
        status_code: int,
        duration: float,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Write request metadata, response status, and duration in milliseconds."""
        extra_data = {
            "method": request.method,
            "path": request.path,
            "status": status_code,
            "duration_ms": round(duration * 1000, 2),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "-"),
            "request_id": getattr(request, "request_id", "unknown"),
        }

        if extra:
            extra_data.update(extra)

        self.logger.info("", extra=extra_data)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client[0]
        return "-"


class AccessMiddleware:
    """Record the status and duration of HTTP requests, including failed calls."""

    def __init__(self, app: Any, logger: AccessLogger | None = None) -> None:
        self.app = app
        self.logger = logger or AccessLogger()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, None)
        start_time = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start_time
            self.logger.log_request(request, status_code, duration)
