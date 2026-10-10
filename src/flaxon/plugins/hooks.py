from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any


class PluginHook:
    """Plugin hook implementation for the plugins subsystem."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._handlers: list[Callable] = []

    def register(self, handler: Callable) -> None:
        """Perform the register operation for plugin hook."""
        self._handlers.append(handler)

    def unregister(self, handler: Callable) -> None:
        """Perform the unregister operation for plugin hook."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    def trigger(self, *args: Any, **kwargs: Any) -> None:
        """Perform the trigger operation for plugin hook."""
        for handler in self._handlers:
            try:
                handler(*args, **kwargs)
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Isolated callback or cleanup failed (%s)", type(exc).__name__
                )

    async def trigger_async(self, *args: Any, **kwargs: Any) -> None:
        """Perform the trigger async operation for plugin hook."""
        for handler in self._handlers:
            try:
                result = handler(*args, **kwargs)
                if hasattr(result, "__await__"):
                    await result
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Isolated callback or cleanup failed (%s)", type(exc).__name__
                )


class PluginHooks:
    """Plugin hooks implementation for the plugins subsystem."""

    def __init__(self) -> None:
        """Perform the   init   operation for plugin hooks."""
        self._hooks: dict[str, PluginHook] = {}

    def get(self, name: str) -> PluginHook:
        """Retrieve the requested value using this object's configured behavior."""
        if name not in self._hooks:
            self._hooks[name] = PluginHook(name)
        return self._hooks[name]

    def register(self, name: str, handler: Callable) -> None:
        """Perform the register operation for plugin hooks."""
        hook = self.get(name)
        hook.register(handler)

    def unregister(self, name: str, handler: Callable) -> None:
        """Perform the unregister operation for plugin hooks."""
        hook = self.get(name)
        hook.unregister(handler)

    def trigger(self, name: str, *args: Any, **kwargs: Any) -> None:
        """Perform the trigger operation for plugin hooks."""
        hook = self.get(name)
        hook.trigger(*args, **kwargs)

    async def trigger_async(self, name: str, *args: Any, **kwargs: Any) -> None:
        """Perform the trigger async operation for plugin hooks."""
        hook = self.get(name)
        await hook.trigger_async(*args, **kwargs)

    def clear(self) -> None:
        """Remove the stored entries."""
        self._hooks.clear()

    def list_hooks(self) -> list[str]:
        """List the hooks."""
        return list(self._hooks.keys())
