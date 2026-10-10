"""
WebSocket events for Flaxon.

This module provides event handling for WebSocket connections including
connection events, message events, and disconnect events.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .connection import WebSocket


class EventType(Enum):
    """WebSocket event types."""

    CONNECT = "connect"
    DISCONNECT = "disconnect"
    MESSAGE = "message"
    ERROR = "error"
    JOIN = "join"
    LEAVE = "leave"


@dataclass
class WebSocketEvent:
    """
    WebSocket event.

    Attributes:
        type: The event type.
        socket: The WebSocket connection.
        data: The event data.
        room: The room name (if applicable).
    """

    type: EventType
    socket: WebSocket
    data: Any = None
    room: str | None = None


class EventHandler:
    """
    WebSocket event handler.

    This class manages event listeners and dispatches events.

    Example:
        ```python
        handler = EventHandler()


        @handler.on(EventType.CONNECT)
        async def on_connect(event: WebSocketEvent):
            print(f"Connected: {event.socket}")


        @handler.on(EventType.MESSAGE)
        async def on_message(event: WebSocketEvent):
            print(f"Message: {event.data}")
        ```
    """

    def __init__(self) -> None:
        """Initialize the event handler."""
        self._listeners: dict[EventType, list[Callable]] = {}
        self._once_listeners: dict[EventType, list[Callable]] = {}

    def on(self, event_type: EventType) -> Callable:
        """
        Decorator to register an event listener.

        Args:
            event_type: The event type to listen for.

        Returns:
            A decorator function.

        Example:
            ```python
            @handler.on(EventType.MESSAGE)
            async def handle_message(event: WebSocketEvent):
                print(event.data)
            ```
        """

        def decorator(func: Callable) -> Callable:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(func)
            return func

        return decorator

    def once(self, event_type: EventType) -> Callable:
        """
        Decorator to register a one-time event listener.

        Args:
            event_type: The event type to listen for.

        Returns:
            A decorator function.
        """

        def decorator(func: Callable) -> Callable:
            if event_type not in self._once_listeners:
                self._once_listeners[event_type] = []
            self._once_listeners[event_type].append(func)
            return func

        return decorator

    def add_listener(self, event_type: EventType, func: Callable) -> None:
        """
        Add an event listener.

        Args:
            event_type: The event type to listen for.
            func: The listener function.
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(func)

    def remove_listener(self, event_type: EventType, func: Callable) -> None:
        """
        Remove an event listener.

        Args:
            event_type: The event type.
            func: The listener function to remove.
        """
        if event_type in self._listeners:
            self._listeners[event_type] = [f for f in self._listeners[event_type] if f != func]

    def clear_listeners(self) -> None:
        """Clear all event listeners."""
        self._listeners.clear()
        self._once_listeners.clear()

    async def dispatch(self, event: WebSocketEvent) -> None:
        """
        Dispatch an event to all listeners.

        Args:
            event: The event to dispatch.
        """
        listeners = list(self._listeners.get(event.type, []))
        once_listeners = list(self._once_listeners.get(event.type, []))

        # Clear once_listeners for this type up front
        if event.type in self._once_listeners:
            self._once_listeners[event.type] = []

        for listener in listeners + once_listeners:
            try:
                result = listener(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Isolated callback or cleanup failed (%s)", type(exc).__name__
                )


class WebSocketEvents:
    """
    WebSocket events manager.

    This class provides convenient methods for handling WebSocket events
    on a connection.

    Example:
        ```python
        @app.websocket("/ws/chat")
        async def chat(socket: WebSocket):
            events = WebSocketEvents(socket)

            @events.on_message
            async def handle_message(data: Any):
                await socket.send_json({"echo": data})

            @events.on_disconnect
            async def handle_disconnect(code: int):
                print(f"Disconnected: {code}")

            await events.run()
        ```
    """

    def __init__(self, socket: WebSocket) -> None:
        """
        Initialize the WebSocket events manager.

        Args:
            socket: The WebSocket connection.
        """
        self.socket = socket
        self._message_handlers: list[Callable] = []
        self._connect_handlers: list[Callable] = []
        self._disconnect_handlers: list[Callable] = []
        self._error_handlers: list[Callable] = []
        self._join_handlers: list[Callable] = []
        self._leave_handlers: list[Callable] = []

    def on_message(self, func: Callable) -> Callable:
        """Decorator to register a message handler."""
        self._message_handlers.append(func)
        return func

    def on_connect(self, func: Callable) -> Callable:
        """Decorator to register a connect handler."""
        self._connect_handlers.append(func)
        return func

    def on_disconnect(self, func: Callable) -> Callable:
        """Decorator to register a disconnect handler."""
        self._disconnect_handlers.append(func)
        return func

    def on_error(self, func: Callable) -> Callable:
        """Decorator to register an error handler."""
        self._error_handlers.append(func)
        return func

    def on_join(self, func: Callable) -> Callable:
        """Decorator to register a join handler."""
        self._join_handlers.append(func)
        return func

    def on_leave(self, func: Callable) -> Callable:
        """Decorator to register a leave handler."""
        self._leave_handlers.append(func)
        return func

    async def _call_handlers(self, handlers, value):
        for handler in handlers:
            result = handler(value)
            if asyncio.iscoroutine(result):
                await result

    async def _handle_message(self, data):
        for handler in self._message_handlers:
            try:
                result = handler(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                await self._call_handlers(self._error_handlers, exc)

    async def run(self) -> None:
        """Run connection handlers, deliver messages, and always report disconnection."""
        try:
            await self.socket.accept()
            await self._call_handlers(self._connect_handlers, self.socket)
            async for raw in self.socket:
                data = raw.get("text") if isinstance(raw, dict) else getattr(raw, "text", raw)
                if data is not None:
                    await self._handle_message(data)
        except Exception as exc:
            await self._call_handlers(self._error_handlers, exc)
        finally:
            await self._call_handlers(self._disconnect_handlers, getattr(self.socket, "_close_code", 1000))
