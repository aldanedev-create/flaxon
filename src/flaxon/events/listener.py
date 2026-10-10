from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .event import Event


class Listener:
    """Listener implementation for the events subsystem."""

    def __init__(self, callback: Callable, priority: int = 0) -> None:
        self.callback = callback
        self.priority = priority

    def handle(self, event: Event) -> Any:
        """Process the supplied request or event."""
        return self.callback(event)

    def __lt__(self, other: Listener) -> bool:
        return self.priority > other.priority


class EventListener:
    """Event listener implementation for the events subsystem."""

    def __init__(self, event_name: str, callback: Callable, priority: int = 0) -> None:
        """Perform the   init   operation for event listener."""
        self.event_name = event_name
        self.callback = callback
        self.priority = priority

    def handle(self, event: Event) -> Any:
        """Process the supplied request or event."""
        return self.callback(event)

    def __lt__(self, other: EventListener) -> bool:
        return self.priority > other.priority


def listener(event_name: str | None = None, priority: int = 0) -> Callable:
    """Perform the listener operation for this subsystem."""

    def decorator(func: Callable) -> Callable:
        if event_name:
            func._flaxon_event = event_name
            func._flaxon_priority = priority
        else:
            func._flaxon_event = func.__name__
            func._flaxon_priority = priority
        return func

    return decorator


def on(event_name: str, priority: int = 0) -> Callable:
    """Perform the on operation for this subsystem."""
    return listener(event_name, priority)
