from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any


class PluginHook:
    def __init__(self, name: str) -> None:
        self.name = name
        self._handlers: list[Callable] = []

    def register(self, handler: Callable) -> None:
        self._handlers.append(handler)

    def unregister(self, handler: Callable) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    def trigger(self, *args: Any, **kwargs: Any) -> None:
        for handler in self._handlers:
            try:
                handler(*args, **kwargs)
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Isolated callback or cleanup failed (%s)", type(exc).__name__
                )

    async def trigger_async(self, *args: Any, **kwargs: Any) -> None:
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
    def __init__(self) -> None:
        self._hooks: dict[str, PluginHook] = {}

    def get(self, name: str) -> PluginHook:
        if name not in self._hooks:
            self._hooks[name] = PluginHook(name)
        return self._hooks[name]

    def register(self, name: str, handler: Callable) -> None:
        hook = self.get(name)
        hook.register(handler)

    def unregister(self, name: str, handler: Callable) -> None:
        hook = self.get(name)
        hook.unregister(handler)

    def trigger(self, name: str, *args: Any, **kwargs: Any) -> None:
        hook = self.get(name)
        hook.trigger(*args, **kwargs)

    async def trigger_async(self, name: str, *args: Any, **kwargs: Any) -> None:
        hook = self.get(name)
        await hook.trigger_async(*args, **kwargs)

    def clear(self) -> None:
        self._hooks.clear()

    def list_hooks(self) -> list[str]:
        return list(self._hooks.keys())
