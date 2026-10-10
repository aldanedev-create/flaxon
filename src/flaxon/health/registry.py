from __future__ import annotations

import asyncio
from typing import Any

from .checks import HealthCheck, HealthCheckResult


class HealthRegistry:
    """Health registry implementation for the health subsystem."""

    def __init__(self) -> None:
        self._checks: dict[str, HealthCheck] = {}

    def register(self, check: HealthCheck) -> None:
        """Perform the register operation for health registry."""
        self._checks[check.name] = check

    def register_function(self, name: str, func: Any) -> None:
        """Register the function."""
        self._checks[name] = HealthCheck(name, func)

    def unregister(self, name: str) -> None:
        """Perform the unregister operation for health registry."""
        self._checks.pop(name, None)

    def get(self, name: str) -> HealthCheck | None:
        """Retrieve the requested value using this object's configured behavior."""
        return self._checks.get(name)

    def list_checks(self) -> list[str]:
        """List the checks."""
        return list(self._checks.keys())

    async def run_all(self) -> list[HealthCheckResult]:
        """Perform the run all operation for health registry."""
        tasks = [check.run() for check in self._checks.values()]
        return await asyncio.gather(*tasks)

    async def run_one(self, name: str) -> HealthCheckResult | None:
        """Perform the run one operation for health registry."""
        check = self.get(name)
        if check is None:
            return None
        return await check.run()

    async def run_selected(self, names: list[str]) -> list[HealthCheckResult]:
        """Perform the run selected operation for health registry."""
        tasks = []
        for name in names:
            check = self.get(name)
            if check:
                tasks.append(check.run())
        return await asyncio.gather(*tasks)

    async def run_excluding(self, exclude: list[str]) -> list[HealthCheckResult]:
        """Perform the run excluding operation for health registry."""
        names = [name for name in self._checks if name not in exclude]
        return await self.run_selected(names)

    def clear(self) -> None:
        """Remove the stored entries."""
        self._checks.clear()

    @property
    def count(self) -> int:
        """Return the number of matching entries."""
        return len(self._checks)

    def __len__(self) -> int:
        return len(self._checks)

    def __contains__(self, name: str) -> bool:
        return name in self._checks

    def __iter__(self):
        return iter(self._checks)
