from __future__ import annotations

import time

from .registry import HealthRegistry
from .response import HealthResponse


class LivenessProbe:
    """Liveness probe implementation for the health subsystem."""

    def __init__(self, registry: HealthRegistry) -> None:
        self.registry = registry

    async def check(self) -> HealthResponse:
        """Perform the check operation for liveness probe."""
        results = await self.registry.run_all()

        all_healthy = all(r.is_healthy() for r in results)

        details = {r.name: r.to_dict() for r in results}

        status = "healthy" if all_healthy else "unhealthy"

        return HealthResponse(
            status=status,
            details=details,
        )


class ReadinessProbe:
    """Readiness probe implementation for the health subsystem."""

    def __init__(self, registry: HealthRegistry) -> None:
        """Perform the   init   operation for readiness probe."""
        self.registry = registry
        self._ready = False
        self._ready_since: float | None = None

    def mark_ready(self) -> None:
        """Mark the ready."""
        self._ready = True
        self._ready_since = time.time()

    def mark_not_ready(self) -> None:
        """Mark the not ready."""
        self._ready = False
        self._ready_since = None

    async def check(self) -> HealthResponse:
        """Perform the check operation for readiness probe."""
        if not self._ready:
            return HealthResponse(
                status="unhealthy",
                details={"ready": False, "reason": "Not ready"},
            )

        results = await self.registry.run_all()

        all_healthy = all(r.is_healthy() for r in results)

        details = {r.name: r.to_dict() for r in results}
        details["ready"] = True
        if self._ready_since:
            details["ready_since"] = round(time.time() - self._ready_since, 2)

        status = "healthy" if all_healthy else "unhealthy"

        return HealthResponse(
            status=status,
            details=details,
        )


class StartupProbe:
    """Startup probe implementation for the health subsystem."""

    def __init__(self, registry: HealthRegistry) -> None:
        self.registry = registry
        self._started = False
        self._start_time = time.time()

    def mark_started(self) -> None:
        """Mark the started."""
        self._started = True

    async def check(self) -> HealthResponse:
        """Perform the check operation for startup probe."""
        if not self._started:
            return HealthResponse(
                status="unhealthy",
                details={"started": False},
            )

        results = await self.registry.run_all()

        all_healthy = all(r.is_healthy() for r in results)

        details = {r.name: r.to_dict() for r in results}
        details["started"] = True
        details["startup_time"] = round(time.time() - self._start_time, 2)

        status = "healthy" if all_healthy else "unhealthy"

        return HealthResponse(
            status=status,
            details=details,
        )


class ProbeHandler:
    """Probe handler implementation for the health subsystem."""

    def __init__(
        self,
        registry: HealthRegistry,
        liveness: LivenessProbe | None = None,
        readiness: ReadinessProbe | None = None,
        startup: StartupProbe | None = None,
    ) -> None:
        self.registry = registry
        self.liveness = liveness or LivenessProbe(registry)
        self.readiness = readiness or ReadinessProbe(registry)
        self.startup = startup or StartupProbe(registry)

    async def liveness_check(self) -> HealthResponse:
        """Perform the liveness check operation for probe handler."""
        return await self.liveness.check()

    async def readiness_check(self) -> HealthResponse:
        """Perform the readiness check operation for probe handler."""
        return await self.readiness.check()

    async def startup_check(self) -> HealthResponse:
        """Perform the startup check operation for probe handler."""
        return await self.startup.check()

    def mark_ready(self) -> None:
        """Mark the ready."""
        self.readiness.mark_ready()

    def mark_not_ready(self) -> None:
        """Mark the not ready."""
        self.readiness.mark_not_ready()

    def mark_started(self) -> None:
        """Mark the started."""
        self.startup.mark_started()
