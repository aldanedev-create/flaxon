from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any


class Fixture:
    """Fixture implementation for the testing subsystem."""

    def __init__(self, name: str, setup: Callable, teardown: Callable | None = None) -> None:
        self.name = name
        self.setup = setup
        self.teardown = teardown
        self._instance: Any = None

    async def load(self) -> Any:
        """Load the requested resource using the configured source."""
        if self._instance is not None:
            return self._instance

        result = self.setup()
        if asyncio.iscoroutine(result):
            self._instance = await result
        else:
            self._instance = result

        return self._instance

    async def unload(self) -> None:
        """Perform the unload operation for fixture."""
        if self.teardown and self._instance is not None:
            result = self.teardown(self._instance)
            if asyncio.iscoroutine(result):
                await result
        self._instance = None


class FixtureLoader:
    """Fixture loader implementation for the testing subsystem."""

    def __init__(self) -> None:
        self._fixtures: dict[str, Fixture] = {}

    def register(self, fixture: Fixture) -> None:
        """Perform the register operation for fixture loader."""
        self._fixtures[fixture.name] = fixture

    def register_function(self, name: str, setup: Callable, teardown: Callable | None = None) -> None:
        """Register the function."""
        self.register(Fixture(name, setup, teardown))

    def get(self, name: str) -> Fixture | None:
        """Retrieve the requested value using this object's configured behavior."""
        return self._fixtures.get(name)

    async def load(self, name: str) -> Any:
        """Load the requested resource using the configured source."""
        fixture = self.get(name)
        if fixture is None:
            raise ValueError(f"Fixture '{name}' not found")
        return await fixture.load()

    async def load_all(self) -> dict[str, Any]:
        """Load the all."""
        result = {}
        for name, fixture in self._fixtures.items():
            result[name] = await fixture.load()
        return result

    async def unload(self, name: str) -> None:
        """Perform the unload operation for fixture loader."""
        fixture = self.get(name)
        if fixture:
            await fixture.unload()

    async def unload_all(self) -> None:
        """Perform the unload all operation for fixture loader."""
        for fixture in self._fixtures.values():
            await fixture.unload()

    def clear(self) -> None:
        """Remove the stored entries."""
        self._fixtures.clear()
