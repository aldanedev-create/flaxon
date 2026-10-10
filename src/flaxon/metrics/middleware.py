from __future__ import annotations

import time
from typing import Any

from flaxon.http import Request

from .collector import MetricsCollector


class MetricsMiddleware:
    """Metrics middleware implementation for the metrics subsystem."""

    def __init__(
        self,
        app: Any,
        collector: MetricsCollector | None = None,
        include_path: bool = True,
        include_method: bool = True,
        include_status: bool = True,
    ) -> None:
        self.app = app
        self.collector = collector or MetricsCollector()
        self.include_path = include_path
        self.include_method = include_method
        self.include_status = include_status

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, None)
        start_time = time.perf_counter()
        status_code = 500

        labels = self._get_labels(request)
        active_labels = {"path": request.path} if self.include_path else {}

        self.collector.counter("http_requests_total", "Total HTTP requests").inc(**labels)
        self.collector.gauge("http_requests_active", "Active HTTP requests").inc(**active_labels)

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                if self.include_status:
                    labels["status"] = str(status_code)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = (time.perf_counter() - start_time) * 1000
            if self.include_status:
                labels["status"] = str(status_code)

            self.collector.timer("http_request_duration_ms", "HTTP request duration").observe(
                duration, **labels
            )

            if status_code >= 500:
                self.collector.counter("http_errors_total", "HTTP errors").inc(**labels)
            elif status_code >= 400:
                self.collector.counter("http_client_errors_total", "HTTP client errors").inc(**labels)

            self.collector.gauge("http_requests_active", "Active HTTP requests").dec(**active_labels)

    def _get_labels(self, request: Request) -> dict[str, str]:
        labels = {}

        if self.include_method:
            labels["method"] = request.method

        if self.include_path:
            labels["path"] = request.path

        return labels
