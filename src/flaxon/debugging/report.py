from __future__ import annotations

import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class ReportGenerator:
    """Report generator implementation for the debugging subsystem."""

    def __init__(self) -> None:
        self._reports: list[dict[str, Any]] = []

    def generate_error_report(self, error_data: dict[str, Any]) -> dict[str, Any]:
        """Generate the error report."""
        return {
            "report_id": error_data.get("error_id"),
            "generated_at": datetime.now().isoformat(),
            "error": {
                "type": error_data.get("type"),
                "message": error_data.get("message"),
                "timestamp": error_data.get("timestamp"),
            },
            "request": {
                "method": error_data.get("method"),
                "path": error_data.get("path"),
                "request_id": error_data.get("request_id"),
            },
            "system": self._get_system_info(),
        }

    def generate_summary_report(self, errors: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate the summary report."""
        types = {}
        paths = {}

        for error in errors:
            error_type = error.get("type", "Unknown")
            types[error_type] = types.get(error_type, 0) + 1

            path = error.get("path", "/")
            paths[path] = paths.get(path, 0) + 1

        return {
            "generated_at": datetime.now().isoformat(),
            "total_errors": len(errors),
            "by_type": types,
            "by_path": paths,
            "errors": errors[-10:],
        }

    def generate_performance_report(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Generate the performance report."""
        return {
            "generated_at": datetime.now().isoformat(),
            "performance": metrics,
            "timestamp": time.time(),
        }

    def _get_system_info(self) -> dict[str, Any]:

        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "hostname": platform.node(),
        }

    def to_json(self, report: dict[str, Any], pretty: bool = True) -> str:
        """Convert to the json."""
        if pretty:
            return json.dumps(report, indent=2, default=str)
        return json.dumps(report, default=str)

    def save_report(self, report: dict[str, Any], filename: str) -> None:
        """Save the report."""
        Path("reports").mkdir(parents=True, exist_ok=True)
        path = str(Path("reports") / filename)
        with Path(path).open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
