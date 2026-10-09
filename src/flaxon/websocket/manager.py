"""In-memory WebSocket connection and room manager."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class WebSocketManager:
    """Track connections and broadcast rooms for an application."""

    def __init__(self, broadcaster: Any | None = None) -> None:
        self.connections: set[Any] = set()
        self.rooms: dict[str, set[Any]] = defaultdict(set)
        self.broadcaster = broadcaster
        self._listeners: dict[str, asyncio.Task[Any]] = {}

    async def configure_broadcaster(self, broadcaster: Any, rooms: set[str] | None = None) -> None:
        """Enable cross-worker room broadcasts using a Broadcaster implementation."""
        self.broadcaster = broadcaster
        for room in rooms or set(self.rooms):
            if room not in self._listeners:
                self._listeners[room] = asyncio.create_task(self._listen(room))

    async def _listen(self, room: str) -> None:
        async for value in self.broadcaster.subscribe(room):
            for socket in tuple(self.rooms.get(room, ())):
                await socket.send_json(value)

    async def connect(self, socket: Any) -> None:
        self.connections.add(socket)

    async def disconnect(self, socket: Any) -> None:
        self.connections.discard(socket)
        for members in self.rooms.values():
            members.discard(socket)

    async def join(self, room: str, socket: Any) -> None:
        self.rooms[room].add(socket)

    async def leave(self, room: str, socket: Any) -> None:
        self.rooms[room].discard(socket)

    async def broadcast_json(self, room: str, value: Any) -> None:
        if self.broadcaster is not None:
            await self.broadcaster.publish(room, value)
            if room in self._listeners:
                return
        for socket in tuple(self.rooms.get(room, ())):
            await socket.send_json(value)

    async def close_broadcaster(self) -> None:
        for task in self._listeners.values():
            task.cancel()
        self._listeners.clear()
