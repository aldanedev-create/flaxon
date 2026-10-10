from __future__ import annotations

from typing import Any

from .plugin import Plugin


class PluginRegistry:
    """Plugin registry implementation for the plugins subsystem."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        """Perform the register operation for plugin registry."""
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin '{plugin.name}' is already registered")
        self._plugins[plugin.name] = plugin

    def unregister(self, name: str) -> None:
        """Perform the unregister operation for plugin registry."""
        if name in self._plugins:
            del self._plugins[name]

    def get(self, name: str) -> Plugin | None:
        """Retrieve the requested value using this object's configured behavior."""
        return self._plugins.get(name)

    def has(self, name: str) -> bool:
        """Perform the has operation for plugin registry."""
        return name in self._plugins

    def list(self) -> list[str]:
        """Return the matching entries."""
        return list(self._plugins.keys())

    def get_all(self) -> list[Plugin]:
        """Return all matching stored entries."""
        return list(self._plugins.values())

    def clear(self) -> None:
        """Remove the stored entries."""
        self._plugins.clear()

    def get_metadata(self) -> dict[str, dict[str, Any]]:
        """Return the configured metadata."""
        return {name: plugin.get_metadata() for name, plugin in self._plugins.items()}

    def __len__(self) -> int:
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        return self.has(name)

    def __iter__(self):
        return iter(self._plugins)
