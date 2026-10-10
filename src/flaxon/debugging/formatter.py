from __future__ import annotations

import json
import traceback
from datetime import datetime
from typing import Any


class Formatter:
    """Formatter implementation for the debugging subsystem."""

    def __init__(self) -> None:
        self._indent = 2

    def format_error(self, error: Exception, request_id: str | None = None) -> dict[str, Any]:
        """Format the error."""
        return {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id or "unknown",
            "error": {
                "type": type(error).__name__,
                "message": str(error),
            },
        }

    def format_traceback(self, error: Exception, limit: int = 20) -> str:
        """Format the traceback."""
        return "".join(traceback.format_exception(type(error), error, error.__traceback__, limit=limit))

    def format_snapshot(self, snapshot: dict[str, Any]) -> str:
        """Format the snapshot."""
        return json.dumps(snapshot, indent=self._indent, default=str)

    def format_validation_errors(self, errors: dict[str, list[str]]) -> str:
        """Format the validation errors."""
        lines = ["Validation Errors:"]
        for field, field_errors in errors.items():
            lines.append(f"  {field}:")
            for error in field_errors:
                lines.append(f"    - {error}")
        return "\n".join(lines)

    def format_headers(self, headers: dict[str, str]) -> str:
        """Format the headers."""
        lines = ["Headers:"]
        for key, value in headers.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def format_request(self, request_data: dict[str, Any]) -> str:
        """Format the request."""
        lines = ["Request:"]
        lines.append(f"  Method: {request_data.get('method', 'UNKNOWN')}")
        lines.append(f"  Path: {request_data.get('path', '/')}")
        if request_data.get("query"):
            lines.append(f"  Query: {request_data.get('query')}")
        if request_data.get("headers"):
            lines.append("  Headers:")
            for key, value in request_data.get("headers", {}).items():
                lines.append(f"    {key}: {value}")
        if request_data.get("body"):
            lines.append(f"  Body: {request_data.get('body')[:200]}")
        return "\n".join(lines)

    def format_response(self, response_data: dict[str, Any]) -> str:
        """Format the response."""
        lines = ["Response:"]
        lines.append(f"  Status: {response_data.get('status', 200)}")
        if response_data.get("headers"):
            lines.append("  Headers:")
            for key, value in response_data.get("headers", {}).items():
                lines.append(f"    {key}: {value}")
        if response_data.get("body"):
            lines.append(f"  Body: {response_data.get('body')[:200]}")
        return "\n".join(lines)

    def format_duration(self, duration: float) -> str:
        """Format the duration."""
        if duration < 1:
            return f"{duration * 1000:.2f}ms"
        return f"{duration:.2f}s"

    def to_json(self, data: Any, pretty: bool = True) -> str:
        """Convert to the json."""
        if pretty:
            return json.dumps(data, indent=self._indent, default=str, ensure_ascii=False)
        return json.dumps(data, default=str, ensure_ascii=False)
