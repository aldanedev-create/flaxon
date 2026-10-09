"""WebSocket broadcaster for Flaxon.

This module provides broadcasting capabilities for WebSocket messages
across multiple workers or servers.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from .connection import WebSocket


class Broadcaster(ABC):
    """WebSocket message broadcaster.

    This abstract class defines the interface for broadcasting messages
    across multiple workers or servers.

    Example:
        ```python
        class RedisBroadcaster(Broadcaster):

            async def publish(self, channel: str, message: Any) -> None:
                await self.redis.publish(channel, json.dumps(message))

            async def subscribe(self, channel: str) -> AsyncIterator[Any]:
                async for message in self.redis.subscribe(channel):
                    yield json.loads(message)
        ```
    """

    @abstractmethod
    async def publish(self, channel: str, message: Any) -> None:
        """Publish a message to a channel.

        Args:
            channel: The channel name.
            message: The message to publish.
        """
        pass

    @abstractmethod
    async def subscribe(self, channel: str) -> AsyncIterator[Any]:
        """Subscribe to a channel.

        Args:
            channel: The channel name.

        Returns:
            An async iterator of messages.
        """
        pass


class MemoryBroadcaster(Broadcaster):
    """In-memory broadcaster for single-process deployments.

    This broadcaster uses asyncio queues for message passing within a
    single process.
    """

    def __init__(self) -> None:
        """Initialize the memory broadcaster."""
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, channel: str, message: Any) -> None:
        """Publish a message to a channel.

        Args:
            channel: The channel name.
            message: The message to publish.
        """
        async with self._lock:
            queues = list(self._subscribers.get(channel, []))

        for queue in queues:
            await queue.put(message)

    async def subscribe(self, channel: str) -> AsyncIterator[Any]:
        """Subscribe to a channel.

        Args:
            channel: The channel name.

        Returns:
            An async iterator of messages.
        """
        queue: asyncio.Queue = asyncio.Queue()

        async with self._lock:
            if channel not in self._subscribers:
                self._subscribers[channel] = []
            self._subscribers[channel].append(queue)

        try:
            while True:
                message = await queue.get()
                yield message
        finally:
            async with self._lock:
                if channel in self._subscribers:
                    self._subscribers[channel] = [
                        q for q in self._subscribers[channel] if q != queue
                    ]
                    if not self._subscribers[channel]:
                        del self._subscribers[channel]


class BroadcastManager:
    """Broadcast manager for WebSocket connections.

    This class manages broadcasting to WebSocket connections using
    a broadcaster backend.

    Example:
        ```python
        manager = BroadcastManager(MemoryBroadcaster())


        @app.websocket("/ws/chat")
        async def chat(socket: WebSocket):
            await socket.accept()
            async for message in socket.iter_json():
                await manager.broadcast("chat", message)
        ```
    """

    def __init__(self, broadcaster: Broadcaster | None = None) -> None:
        """Initialize the broadcast manager.

        Args:
            broadcaster: The broadcaster backend.
        """
        self.broadcaster = broadcaster or MemoryBroadcaster()
        self._connections: dict[str, set[WebSocket]] = {}
        self._listener_tasks: set[asyncio.Task] = set()
        self._lock = asyncio.Lock()

    async def broadcast(self, channel: str, message: Any) -> None:
        """Broadcast a message to a channel.

        Args:
            channel: The channel name.
            message: The message to broadcast.
        """
        await self.broadcaster.publish(channel, message)

    async def broadcast_json(self, channel: str, data: Any) -> None:
        """Broadcast a JSON message to a channel.

        Args:
            channel: The channel name.
            data: The data to broadcast.
        """
        await self.broadcaster.publish(channel, {"type": "json", "data": data})

    async def broadcast_text(self, channel: str, text: str) -> None:
        """Broadcast a text message to a channel.

        Args:
            channel: The channel name.
            text: The text to broadcast.
        """
        await self.broadcaster.publish(channel, {"type": "text", "data": text})

    async def register(self, channel: str, socket: WebSocket) -> None:
        """Register a WebSocket connection to receive broadcasts.

        Args:
            channel: The channel name.
            socket: The WebSocket connection.
        """
        async with self._lock:
            if channel not in self._connections:
                self._connections[channel] = set()
                task = asyncio.create_task(self._listen(channel))
                self._listener_tasks.add(task)
                task.add_done_callback(self._listener_tasks.discard)
            self._connections[channel].add(socket)

    async def unregister(self, channel: str, socket: WebSocket) -> None:
        """Unregister a WebSocket connection.

        Args:
            channel: The channel name.
            socket: The WebSocket connection.
        """
        async with self._lock:
            if channel in self._connections:
                self._connections[channel].discard(socket)
                if not self._connections[channel]:
                    del self._connections[channel]

    async def _listen(self, channel: str) -> None:
        """Listen for messages on a channel and broadcast to connections."""
        async for message in self.broadcaster.subscribe(channel):
            async with self._lock:
                sockets = set(self._connections.get(channel, set()))

            if not sockets:
                break

            failed = []

            for socket in sockets:
                try:
                    if isinstance(message, dict) and message.get("type") == "json":
                        await socket.send_json(message.get("data", {}))
                    elif isinstance(message, dict) and message.get("type") == "text":
                        await socket.send_text(message.get("data", ""))
                    else:
                        await socket.send_text(str(message))
                except Exception:
                    failed.append(socket)

            if failed:
                async with self._lock:
                    for socket in failed:
                        if channel in self._connections:
                            self._connections[channel].discard(socket)