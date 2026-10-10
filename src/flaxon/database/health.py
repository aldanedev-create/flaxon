from __future__ import annotations

import time
from typing import Any

from .manager import DatabaseManager


class DatabaseHealthCheck:
    """Database health check implementation for the database subsystem."""

    def __init__(self, db: DatabaseManager, name: str = "database") -> None:
        self.db = db
        self.name = name

    async def check(self) -> dict[str, Any]:
        """Perform the check operation for database health check."""
        start = time.perf_counter()

        try:
            await self.db.fetch_val("SELECT 1")
            latency = (time.perf_counter() - start) * 1000

            return {
                "name": self.name,
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "pool_size": self.db.pool_size,
                "available": self.db.available_connections,
            }
        except Exception as exc:
            return {
                "name": self.name,
                "status": "unhealthy",
                "error": str(exc),
            }

    async def is_healthy(self) -> bool:
        """Return whether healthy holds for the current value."""
        result = await self.check()
        return result["status"] == "healthy"


class HealthRegistry:
    """Health registry implementation for the database subsystem."""

    def __init__(self) -> None:
        """Perform the   init   operation for health registry."""
        self._checks: dict[str, Any] = {}

    def register(self, name: str, check: Any) -> None:
        """Perform the register operation for health registry."""
        self._checks[name] = check

    def unregister(self, name: str) -> None:
        """Perform the unregister operation for health registry."""
        self._checks.pop(name, None)

    async def check_all(self) -> dict[str, Any]:
        """Check the all."""
        results = {}
        for name, check in self._checks.items():
            if hasattr(check, "check"):
                results[name] = await check.check()
            else:
                results[name] = await check()
        return results

    async def check_one(self, name: str) -> dict[str, Any] | None:
        """Check the one."""
        check = self._checks.get(name)
        if check is None:
            return None

        if hasattr(check, "check"):
            return await check.check()
        return await check()

    async def overall_status(self) -> dict[str, Any]:
        """Perform the overall status operation for health registry."""
        results = await self.check_all()
        all_healthy = all(r.get("status") == "healthy" for r in results.values())

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": results,
            "timestamp": time.time(),
        }
