"""
WebSocket room management for Flaxon.

This module provides room management for WebSocket connections.
"""

from __future__ import annotations

import asyncio
from typing import Any

from .connection import WebSocket


class Room:
    """
    WebSocket room.

    This class represents a room that WebSocket connections can join.

    Attributes:
        name: The room name.
        connections: The connections in the room.
    """

    def __init__(self, name: str) -> None:
        """
        Initialize the room.

        Args:
            name: The room name.
        """
        self.name = name
        self.connections: set[WebSocket] = set()
        self.metadata: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def add(self, socket: WebSocket) -> None:
        """
        Add a connection to the room.

        Args:
            socket: The WebSocket connection.
        """
        async with self._lock:
            self.connections.add(socket)

    async def remove(self, socket: WebSocket) -> None:
        """
        Remove a connection from the room.

        Args:
            socket: The WebSocket connection.
        """
        async with self._lock:
            self.connections.discard(socket)

    async def broadcast_text(self, message: str) -> None:
        """
        Broadcast a text message to all connections in the room concurrently.

        Args:
            message: The text to broadcast.
        """
        async with self._lock:
            targets = list(self.connections)

        if not targets:
            return

        results = await asyncio.gather(
            *(socket.send_text(message) for socket in targets),
            return_exceptions=True,
        )

        failed = [socket for socket, res in zip(targets, results, strict=True) if isinstance(res, Exception)]

        if failed:
            async with self._lock:
                for socket in failed:
                    self.connections.discard(socket)

    async def broadcast_json(self, data: Any) -> None:
        """
        Broadcast a JSON message to all connections in the room concurrently.

        Args:
            data: The data to broadcast.
        """
        async with self._lock:
            targets = list(self.connections)

        if not targets:
            return

        results = await asyncio.gather(
            *(socket.send_json(data) for socket in targets),
            return_exceptions=True,
        )

        failed = [socket for socket, res in zip(targets, results, strict=True) if isinstance(res, Exception)]

        if failed:
            async with self._lock:
                for socket in failed:
                    self.connections.discard(socket)

    @property
    def size(self) -> int:
        """Get the number of connections in the room."""
        return len(self.connections)

    def is_empty(self) -> bool:
        """Check if the room is empty."""
        return len(self.connections) == 0


class RoomManager:
    """
    Room manager.

    This class manages WebSocket rooms.

    Example:
        ```python
        manager = RoomManager()


        @app.websocket("/ws/chat")
        async def chat(socket: WebSocket):
            await socket.accept()
            room = await manager.get_or_create("general")
            await room.add(socket)
            try:
                async for message in socket.iter_json():
                    await room.broadcast_json(message)
            finally:
                await room.remove(socket)
        ```
    """

    def __init__(self) -> None:
        """Initialize the room manager."""
        self._rooms: dict[str, Room] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, name: str) -> Room:
        """
        Get a room by name, creating it if it doesn't exist.

        Args:
            name: The room name.

        Returns:
            The room.
        """
        async with self._lock:
            if name not in self._rooms:
                self._rooms[name] = Room(name)
            return self._rooms[name]

    async def get(self, name: str) -> Room | None:
        """
        Get a room by name.

        Args:
            name: The room name.

        Returns:
            The room or None if it doesn't exist.
        """
        async with self._lock:
            return self._rooms.get(name)

    async def delete(self, name: str) -> None:
        """
        Delete a room.

        Args:
            name: The room name.
        """
        async with self._lock:
            room = self._rooms.pop(name, None)

        if room:
            async with room._lock:
                room.connections.clear()

    async def delete_empty(self) -> None:
        """Delete all empty rooms."""
        async with self._lock:
            empty = [name for name, room in self._rooms.items() if room.is_empty()]
            for name in empty:
                del self._rooms[name]

    async def broadcast_text(self, room_name: str, message: str) -> None:
        """
        Broadcast a text message to a room.

        Args:
            room_name: The room name.
            message: The text to broadcast.
        """
        room = await self.get(room_name)
        if room:
            await room.broadcast_text(message)

    async def broadcast_json(self, room_name: str, data: Any) -> None:
        """
        Broadcast a JSON message to a room.

        Args:
            room_name: The room name.
            data: The data to broadcast.
        """
        room = await self.get(room_name)
        if room:
            await room.broadcast_json(data)

    def list_rooms(self) -> list[str]:
        """List all room names."""
        return list(self._rooms.keys())

    @property
    def room_count(self) -> int:
        """Get the number of rooms."""
        return len(self._rooms)

    def total_connections(self) -> int:
        """Get the total number of connections across all rooms."""
        return sum(room.size for room in self._rooms.values())

    def clear(self) -> None:
        """Clear all rooms."""
        self._rooms.clear()
