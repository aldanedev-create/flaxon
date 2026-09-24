"""
Application lifecycle management.

This module handles startup and shutdown callbacks with async support.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, AsyncExitStack
from typing import Any


async def call_maybe_async(callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Call a callback that may be async or sync.

    Args:
        callback: The callback function to call.
        *args: Positional arguments to pass.
        **kwargs: Keyword arguments to pass.

    Returns:
        The result of the callback.
    """
    result = callback(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


class Lifecycle:
    """
    Manages application lifecycle events.

    Handles startup and shutdown callbacks, executing them in the correct order.
    """

    def __init__(self) -> None:
        """Initialize lifecycle manager."""
        self.startup_handlers: list[Callable[..., Any]] = []
        self.shutdown_handlers: list[Callable[..., Any]] = []
        self._context_factories: list[Callable[[], AbstractAsyncContextManager[Any]]] = []
        self._context_stack: AsyncExitStack | None = None

    def on_startup(self, callback: Callable[..., Any]) -> Callable[..., Any]:
        """Register a startup callback."""
        self.startup_handlers.append(callback)
        return callback

    def on_shutdown(self, callback: Callable[..., Any]) -> Callable[..., Any]:
        """Register a shutdown callback."""
        self.shutdown_handlers.append(callback)
        return callback

    def add_lifespan_context(
        self, factory: Callable[[], AbstractAsyncContextManager[Any]]
    ) -> Callable[[], AbstractAsyncContextManager[Any]]:
        """Register an async context manager for the application lifespan.

        Contexts are entered before startup callbacks and exited after shutdown
        callbacks. This allows mounted ASGI applications to share the parent
        application's lifecycle without taking ownership of the ASGI lifespan
        scope themselves.
        """
        self._context_factories.append(factory)
        return factory

    async def startup(self) -> None:
        """Execute all startup handlers in registration order."""
        if self._context_stack is not None:
            return

        stack = AsyncExitStack()
        try:
            await stack.__aenter__()
            for factory in self._context_factories:
                await stack.enter_async_context(factory())
            for callback in self.startup_handlers:
                await call_maybe_async(callback)
        except Exception:
            await stack.aclose()
            raise
        self._context_stack = stack

    async def shutdown(self) -> None:
        """Execute all shutdown handlers in reverse registration order."""
        try:
            for callback in reversed(self.shutdown_handlers):
                await call_maybe_async(callback)
        finally:
            if self._context_stack is not None:
                stack = self._context_stack
                self._context_stack = None
                await stack.aclose()

    def clear(self) -> None:
        """Clear all registered handlers."""
        self.startup_handlers.clear()
        self.shutdown_handlers.clear()
        self._context_factories.clear()
        self._context_stack = None

    @property
    def handler_count(self) -> int:
        """Get the total number of registered handlers."""
        return len(self.startup_handlers) + len(self.shutdown_handlers)

    @property
    def startup_count(self) -> int:
        """Get the number of registered startup handlers."""
        return len(self.startup_handlers)

    @property
    def shutdown_count(self) -> int:
        """Get the number of registered shutdown handlers."""
        return len(self.shutdown_handlers)
