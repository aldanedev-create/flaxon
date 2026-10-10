from __future__ import annotations

import asyncio
from typing import Any

from flaxon.logging import get_logger

from .event import Event
from .listener import Listener
from .registry import EventRegistry

logger = get_logger(__name__)


class EventDispatcher:
    """Event dispatcher implementation for the events subsystem."""

    def __init__(self, registry: EventRegistry | None = None) -> None:
        self.registry = registry or EventRegistry()

    def dispatch(self, event: Event | str, data: Any = None) -> None:
        """Dispatch the supplied event to its registered handlers."""
        if isinstance(event, str):
            event = Event(event, data)

        listeners = self.registry.get_listeners(event.name)

        for listener in listeners:
            try:
                result = listener.handle(event)
                if asyncio.iscoroutine(result):
                    task = asyncio.create_task(result)
                    task.add_done_callback(self._log_task_exception(event.name))
            except Exception:
                logger.exception(f"Error in listener for event '{event.name}'")

    async def dispatch_async(self, event: Event | str, data: Any = None) -> None:
        """Dispatch the async."""
        if isinstance(event, str):
            event = Event(event, data)

        listeners = self.registry.get_listeners(event.name)

        tasks = []
        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener.callback):
                    tasks.append(asyncio.create_task(listener.handle(event)))
                else:
                    tasks.append(asyncio.create_task(self._run_sync(listener, event)))
            except Exception:
                logger.exception(f"Error scheduling listener for event '{event.name}'")

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error in listener for event '{event.name}'", exc_info=result)

    async def _run_sync(self, listener: Listener, event: Event) -> None:
        """Perform the  run sync operation for event dispatcher."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, listener.handle, event)

    def dispatch_sync(self, event: Event | str, data: Any = None) -> None:
        """Dispatch the sync."""
        if isinstance(event, str):
            event = Event(event, data)

        listeners = self.registry.get_listeners(event.name)

        for listener in listeners:
            try:
                listener.handle(event)
            except Exception:
                logger.exception(f"Error in listener for event '{event.name}'")

    async def dispatch_with_response(self, event: Event | str, data: Any = None) -> list[Any]:
        """Dispatch the with response."""
        if isinstance(event, str):
            event = Event(event, data)

        listeners = self.registry.get_listeners(event.name)
        results = []

        for listener in listeners:
            try:
                result = listener.handle(event)
                if asyncio.iscoroutine(result):
                    result = await result
                results.append(result)
            except Exception:
                logger.exception(f"Error in listener for event '{event.name}'")

        return results

    @staticmethod
    def _log_task_exception(event_name: str):
        def callback(task: asyncio.Task) -> None:
            if task.cancelled():
                return
            exc = task.exception()
            if exc is not None:
                logger.error(f"Error in async listener for event '{event_name}'", exc_info=exc)

        return callback

    def has_listeners(self, event_name: str) -> bool:
        """Return whether the requested listeners is available."""
        return len(self.registry.get_listeners(event_name)) > 0

    def get_listener_count(self, event_name: str) -> int:
        """Return the listener count."""
        return len(self.registry.get_listeners(event_name))

    def clear(self) -> None:
        """Remove the stored entries."""
        self.registry.clear()
