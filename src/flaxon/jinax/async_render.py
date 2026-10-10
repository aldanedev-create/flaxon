from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any


class AsyncRenderer:
    """Async renderer implementation for the jinax subsystem."""

    def __init__(self, environment: Any) -> None:
        self.environment = environment

    async def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render the requested content using the supplied context."""
        template = self.environment.get_template(template_name)
        if hasattr(template, "render_async"):
            return await template.render_async(**context)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, template.render, context)

    async def render_string(self, source: str, context: dict[str, Any]) -> str:
        """Render the string."""
        template = self.environment.from_string(source)
        if hasattr(template, "render_async"):
            return await template.render_async(**context)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, template.render, context)

    async def render_many(self, templates: list[tuple[str, dict[str, Any]]]) -> list[str]:
        """Render the many."""
        tasks = [self.render(name, ctx) for name, ctx in templates]
        return await asyncio.gather(*tasks)


class AsyncFilter:
    """Async filter implementation for the jinax subsystem."""

    def __init__(self, func: Callable) -> None:
        self.func = func

    async def apply(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Perform the apply operation for async filter."""
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(value, *args, **kwargs)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.func, value, *args, **kwargs)


class AsyncFunction:
    """Async function implementation for the jinax subsystem."""

    def __init__(self, func: Callable) -> None:
        """Perform the   init   operation for async function."""
        self.func = func

    async def call(self, *args: Any, **kwargs: Any) -> Any:
        """Invoke the supplied callable with its configured arguments."""
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(*args, **kwargs)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.func, *args, **kwargs)


def async_render(func: Callable) -> Callable:
    """Perform the async render operation for this subsystem."""

    async def wrapper(*args: Any, **kwargs: Any) -> str:
        """Perform the wrapper operation for this subsystem."""
        result = func(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result

    return wrapper


class AsyncTemplateCache:
    """Async template cache implementation for the jinax subsystem."""

    def __init__(self, cache: Any) -> None:
        self.cache = cache

    async def get(self, key: str) -> Any:
        """Retrieve the requested value using this object's configured behavior."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.cache.get, key)

    async def set(self, key: str, value: Any) -> None:
        """Store the supplied value under its key."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.cache.set, key, value)

    async def invalidate(self, key: str) -> None:
        """Perform the invalidate operation for async template cache."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.cache.invalidate, key)
