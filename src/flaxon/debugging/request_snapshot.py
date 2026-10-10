from __future__ import annotations

import time
from typing import Any


class RequestSnapshot:
    """Request snapshot implementation for the debugging subsystem."""

    def __init__(self, request: Any) -> None:
        self.request = request
        self.timestamp = time.time()
        self.method = getattr(request, "method", "UNKNOWN")
        self.path = getattr(request, "path", "/")
        self.headers = self._capture_headers()
        self.query = self._capture_query()
        self.cookies = self._capture_cookies()
        self.path_params = self._capture_path_params()
        self.client = self._capture_client()
        self.body = self._capture_body()

    def _capture_headers(self) -> dict[str, str]:
        if hasattr(self.request, "headers"):
            return dict(self.request.headers.items())
        return {}

    def _capture_query(self) -> dict[str, Any]:
        if hasattr(self.request, "query"):
            return dict(self.request.query)
        return {}

    def _capture_cookies(self) -> dict[str, str]:
        if hasattr(self.request, "cookies"):
            return dict(self.request.cookies)
        return {}

    def _capture_path_params(self) -> dict[str, Any]:
        if hasattr(self.request, "path_params"):
            return dict(self.request.path_params)
        return {}

    def _capture_client(self) -> tuple[str, int] | None:
        if hasattr(self.request, "client"):
            return self.request.client
        return None

    def _capture_body(self) -> str | None:
        if hasattr(self.request, "_body") and self.request._body:
            try:
                return self.request._body[:1000].decode("utf-8")
            except UnicodeDecodeError:
                return "<binary data>"
        return None

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        return {
            "timestamp": self.timestamp,
            "method": self.method,
            "path": self.path,
            "headers": self.headers,
            "query": self.query,
            "cookies": self.cookies,
            "path_params": self.path_params,
            "client": self.client,
            "body": self.body,
        }

    @classmethod
    def from_request(cls, request: Any) -> RequestSnapshot | None:
        """Construct from the request."""
        if request is None:
            return None
        try:
            return cls(request)
        except Exception:
            return None
