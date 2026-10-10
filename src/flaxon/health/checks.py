from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HealthCheckResult:
    """Health check result implementation for the health subsystem."""

    name: str
    status: str
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def is_healthy(self) -> bool:
        """Return whether healthy holds for the current value."""
        return self.status == "healthy"

    def is_unhealthy(self) -> bool:
        """Return whether unhealthy holds for the current value."""
        return self.status == "unhealthy"

    def is_degraded(self) -> bool:
        """Return whether degraded holds for the current value."""
        return self.status == "degraded"

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "latency_ms": round(self.latency_ms, 2),
            "timestamp": self.timestamp,
        }


class HealthCheck:
    """Health check implementation for the health subsystem."""

    def __init__(self, name: str, check_func: Callable, timeout: float = 5.0) -> None:
        self.name = name
        self.check_func = check_func
        self.timeout = timeout

    async def run(self) -> HealthCheckResult:
        """Run the configured operation."""
        start = time.perf_counter()

        try:
            result = await asyncio.wait_for(
                self._run_check(),
                timeout=self.timeout,
            )
            latency = (time.perf_counter() - start) * 1000

            if isinstance(result, HealthCheckResult):
                result.latency_ms = latency
                return result

            if isinstance(result, bool):
                status = "healthy" if result else "unhealthy"
                return HealthCheckResult(
                    name=self.name,
                    status=status,
                    latency_ms=latency,
                )

            if isinstance(result, dict):
                status = result.get("status", "healthy")
                return HealthCheckResult(
                    name=self.name,
                    status=status,
                    message=result.get("message"),
                    details=result.get("details", {}),
                    latency_ms=latency,
                )

            return HealthCheckResult(
                name=self.name,
                status="healthy",
                latency_ms=latency,
            )

        except TimeoutError:
            return HealthCheckResult(
                name=self.name,
                status="unhealthy",
                message=f"Health check timed out after {self.timeout}s",
            )

        except Exception as exc:
            return HealthCheckResult(
                name=self.name,
                status="unhealthy",
                message=str(exc),
            )

    async def _run_check(self) -> Any:
        result = self.check_func()
        if hasattr(result, "__await__"):
            return await result
        return result


class DatabaseHealthCheck(HealthCheck):
    """Database health check implementation for the health subsystem."""

    def __init__(self, db_manager: Any, name: str = "database") -> None:
        self.db_manager = db_manager
        super().__init__(name, self._check)

    async def _check(self) -> dict[str, Any]:
        try:
            start = time.perf_counter()
            await self.db_manager.fetch_val("SELECT 1")
            latency = (time.perf_counter() - start) * 1000

            return {
                "status": "healthy",
                "details": {
                    "pool_size": getattr(self.db_manager, "pool_size", 0),
                    "available": getattr(self.db_manager, "available_connections", 0),
                    "latency_ms": round(latency, 2),
                },
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "message": str(exc),
            }


class RedisHealthCheck(HealthCheck):
    """Redis health check implementation for the health subsystem."""

    def __init__(self, redis_client: Any, name: str = "redis") -> None:
        self.redis_client = redis_client
        super().__init__(name, self._check)

    async def _check(self) -> dict[str, Any]:
        try:
            start = time.perf_counter()
            await self.redis_client.ping()
            latency = (time.perf_counter() - start) * 1000

            return {
                "status": "healthy",
                "details": {
                    "latency_ms": round(latency, 2),
                },
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "message": str(exc),
            }


class CompositeHealthCheck(HealthCheck):
    """Composite health check implementation for the health subsystem."""

    def __init__(self, name: str, checks: list[HealthCheck]) -> None:
        self.checks = checks
        super().__init__(name, self._check)

    async def _check(self) -> dict[str, Any]:
        results = []
        all_healthy = True
        degraded = False

        for check in self.checks:
            result = await check.run()
            results.append(result.to_dict())

            if result.is_unhealthy():
                all_healthy = False
            elif result.is_degraded():
                degraded = True

        status = "healthy"
        if not all_healthy:
            status = "unhealthy"
        elif degraded:
            status = "degraded"

        return {
            "status": status,
            "details": {
                "checks": results,
            },
        }
