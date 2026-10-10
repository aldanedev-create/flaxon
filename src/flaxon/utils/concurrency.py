from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")
R = TypeVar("R")


async def run_in_executor(func: Callable[..., R], *args: Any, **kwargs: Any) -> R:
    """Run a synchronous function in a thread pool executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


async def gather_with_concurrency(concurrency: int, *tasks: Any) -> list[Any]:
    """
    Run tasks with limited concurrency.

    Args:
        concurrency: Maximum number of tasks to run concurrently
        *tasks: Tasks to run
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def sem_task(task: Any) -> Any:
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


async def async_map(
    func: Callable[[T], R],
    items: list[T],
    concurrency: int = 10,
) -> list[R]:
    """Map a function over a list with concurrency control."""
    tasks = [asyncio.create_task(async_wrap(func, item)) for item in items]
    return await gather_with_concurrency(concurrency, *tasks)


async def async_wrap(func: Callable[[T], R], item: T) -> R:
    """Wrap a function to be async-safe."""
    result = func(item)
    if asyncio.iscoroutine(result):
        return await result
    return result


def async_to_sync(coro: Any) -> Any:
    """Run an async function synchronously."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def sync_to_async(func: Callable) -> Callable:
    """Convert a sync function to async."""

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await run_in_executor(func, *args, **kwargs)

    return wrapper


async def sleep(seconds: float) -> None:
    """Sleep for a given number of seconds."""
    await asyncio.sleep(seconds)
