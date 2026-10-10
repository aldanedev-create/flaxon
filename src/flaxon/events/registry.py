from __future__ import annotations

from collections.abc import Callable

from .listener import Listener
from .subscriber import EventSubscriber


class EventRegistry:
    """Event registry implementation for the events subsystem."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = {}

    def register(self, event_name: str, callback: Callable, priority: int = 0) -> None:
        """Perform the register operation for event registry."""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(Listener(callback, priority))
        self._listeners[event_name].sort()

    def register_subscriber(self, subscriber: EventSubscriber) -> None:
        """Register the subscriber."""
        for event_name, listeners in subscriber.get_listeners().items():
            for listener in listeners:
                self.register(event_name, listener.callback, listener.priority)

    def get_listeners(self, event_name: str) -> list[Listener]:
        """Return the listeners."""
        return self._listeners.get(event_name, [])

    def remove(self, event_name: str, callback: Callable) -> None:
        """Perform the remove operation for event registry."""
        if event_name in self._listeners:
            self._listeners[event_name] = [
                listener for listener in self._listeners[event_name] if listener.callback != callback
            ]
            if not self._listeners[event_name]:
                del self._listeners[event_name]

    def remove_all(self, event_name: str) -> None:
        """Remove the all."""
        self._listeners.pop(event_name, None)

    def has_listeners(self, event_name: str) -> bool:
        """Return whether the requested listeners is available."""
        return event_name in self._listeners and bool(self._listeners[event_name])

    def clear(self) -> None:
        """Remove the stored entries."""
        self._listeners.clear()

    def get_event_names(self) -> list[str]:
        """Return the event names."""
        return list(self._listeners.keys())

    def get_listener_count(self, event_name: str) -> int:
        """Return the listener count."""
        return len(self._listeners.get(event_name, []))

    def get_total_listener_count(self) -> int:
        """Return the total listener count."""
        return sum(len(listeners) for listeners in self._listeners.values())
