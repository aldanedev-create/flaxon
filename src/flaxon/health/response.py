from __future__ import annotations

import time
from typing import Any

from flaxon.http import JSONResponse


class HealthResponse:
    """Health response implementation for the health subsystem."""

    def __init__(
        self,
        status: str = "healthy",
        details: dict[str, Any] | None = None,
        version: str | None = None,
        uptime: float | None = None,
    ) -> None:
        self.status = status
        self.details = details or {}
        self.version = version
        self.uptime = uptime
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        result = {
            "status": self.status,
            "timestamp": self.timestamp,
        }

        if self.version:
            result["version"] = self.version

        if self.uptime:
            result["uptime"] = round(self.uptime, 2)

        if self.details:
            result["details"] = self.details

        return result

    def to_response(self) -> JSONResponse:
        """Convert to the response."""
        status_code = 200 if self.status == "healthy" else 503
        return JSONResponse(self.to_dict(), status_code=status_code)


class HealthResponseBuilder:
    """Health response builder implementation for the health subsystem."""

    def __init__(self) -> None:
        """Perform the   init   operation for health response builder."""
        self._status = "healthy"
        self._details: dict[str, Any] = {}
        self._version: str | None = None
        self._uptime: float | None = None

    def status(self, status: str) -> HealthResponseBuilder:
        """Return the current status."""
        self._status = status
        return self

    def healthy(self) -> HealthResponseBuilder:
        """Perform the healthy operation for health response builder."""
        self._status = "healthy"
        return self

    def degraded(self) -> HealthResponseBuilder:
        """Perform the degraded operation for health response builder."""
        self._status = "degraded"
        return self

    def unhealthy(self) -> HealthResponseBuilder:
        """Perform the unhealthy operation for health response builder."""
        self._status = "unhealthy"
        return self

    def detail(self, key: str, value: Any) -> HealthResponseBuilder:
        """Perform the detail operation for health response builder."""
        self._details[key] = value
        return self

    def details(self, details: dict[str, Any]) -> HealthResponseBuilder:
        """Perform the details operation for health response builder."""
        self._details.update(details)
        return self

    def version(self, version: str) -> HealthResponseBuilder:
        """Perform the version operation for health response builder."""
        self._version = version
        return self

    def uptime(self, uptime: float) -> HealthResponseBuilder:
        """Perform the uptime operation for health response builder."""
        self._uptime = uptime
        return self

    def build(self) -> HealthResponse:
        """Perform the build operation for health response builder."""
        return HealthResponse(
            status=self._status,
            details=self._details,
            version=self._version,
            uptime=self._uptime,
        )

    def build_response(self) -> JSONResponse:
        """Build the response."""
        return self.build().to_response()


def create_health_response(
    status: str = "healthy",
    details: dict[str, Any] | None = None,
    version: str | None = None,
) -> JSONResponse:
    """Create the health response."""
    response = HealthResponse(status, details, version)
    return response.to_response()
