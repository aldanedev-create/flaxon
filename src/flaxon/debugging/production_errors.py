from __future__ import annotations

import time
import uuid
from typing import Any

from flaxon.http import JSONResponse, Response


class ProductionErrorHandler:
    """Production error handler implementation for the debugging subsystem."""

    def __init__(self, error_store: Any) -> None:
        self.error_store = error_store

    async def handle(self, exc: Exception, request: Any | None, scope: dict[str, Any]) -> Response:
        """Process the supplied request or event."""
        error_id = f"fx_{uuid.uuid4().hex[:12]}"
        request_id = scope.get("flaxon.request_id", error_id)

        self.error_store.store({
            "error_id": error_id,
            "request_id": request_id,
            "type": type(exc).__name__,
            "message": str(exc),
            "timestamp": time.time(),
            "path": scope.get("path", "/"),
            "method": scope.get("method", "GET"),
        })

        return JSONResponse(
            {
                "success": False,
                "error": {
                    "code": "FX-SRV-500",
                    "message": "The request could not be completed.",
                    "request_id": request_id,
                    "error_id": error_id,
                },
            },
            status_code=500,
        )

    def get_error_report(self, error_id: str) -> dict[str, Any] | None:
        """Return the error report."""
        return self.error_store.get(error_id)

    def get_recent_errors(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the recent errors."""
        return self.error_store.get_recent(limit)
