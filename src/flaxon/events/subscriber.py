from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .event import Event
from .listener import Listener


class EventSubscriber:
    """Event subscriber implementation for the events subsystem."""

    def __init__(self, name: str | None = None) -> None:
        self.name = name or self.__class__.__name__
        self._listeners: dict[str, list[Listener]] = {}

    def subscribe(self, event_name: str, callback: Callable, priority: int = 0) -> None:
        """Register a subscription for the supplied event or operation."""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(Listener(callback, priority))

    def get_listeners(self) -> dict[str, list[Listener]]:
        """Return the listeners."""
        return self._listeners

    def get_listeners_for_event(self, event_name: str) -> list[Listener]:
        """Return the listeners for event."""
        return self._listeners.get(event_name, [])

    def get_subscribed_events(self) -> list[str]:
        """Return the subscribed events."""
        return list(self._listeners.keys())

    def clear(self) -> None:
        """Remove the stored entries."""
        self._listeners.clear()


def subscriber(name: str | None = None) -> Callable:
    """Perform the subscriber operation for this subsystem."""

    def decorator(cls: type) -> type:
        """Perform the decorator operation for this subsystem."""
        if not hasattr(cls, "get_subscribed_events"):
            cls.get_subscribed_events = lambda self: list(self._listeners.keys())
        return cls

    return decorator


class EventSubscriberMixin:
    """Event subscriber mixin implementation for the events subsystem."""

    def get_subscribed_events(self) -> list[str]:
        """Return the subscribed events."""
        events = []
        for attr_name in dir(self):
            if attr_name.startswith("on_"):
                events.append(attr_name[3:])
        return events

    def handle_event(self, event: Event) -> Any:
        """Perform the handle event operation for event subscriber mixin."""
        method_name = f"on_{event.name}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(event)
        return None
