"""ASGI WebSocket connection wrapper."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from enum import Enum
from typing import Any


class WebSocketState(str, Enum):
    """Connection lifecycle state."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class WebSocketDisconnect(Exception):
    """Raised when a peer disconnects."""


class WebSocket:
    """A convenient interface over ASGI WebSocket messages."""

    def __init__(self, scope: dict[str, Any], receive: Any, send: Any, manager: Any = None) -> None:
        self.scope = scope
        self._receive = receive
        self._send = send
        self.manager = manager
        self.path_params: dict[str, Any] = {}
        self.state = WebSocketState.CONNECTING

    async def accept(self) -> None:
        """Consume the initial handshake message and accept the peer connection."""
        message = await self._receive()
        if message.get("type") != "websocket.connect":
            raise RuntimeError(
                f"Expected 'websocket.connect' as the first message, got {message.get('type')!r}"
            )
        await self._send({"type": "websocket.accept"})
        self.state = WebSocketState.CONNECTED
        if self.manager is not None:
            await self.manager.connect(self)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close the peer connection."""
        if self.state is not WebSocketState.DISCONNECTED:
            await self._send({"type": "websocket.close", "code": code, "reason": reason})
        self.state = WebSocketState.DISCONNECTED
        if self.manager is not None:
            await self.manager.disconnect(self)

    async def receive(self) -> dict[str, Any]:
        """Receive the next ASGI message."""
        message = await self._receive()
        if message.get("type") == "websocket.disconnect":
            self.state = WebSocketState.DISCONNECTED
            if self.manager is not None:
                await self.manager.disconnect(self)
            raise WebSocketDisconnect()
        return message

    async def receive_text(self) -> str:
        """Receive a text message."""
        return str((await self.receive()).get("text", ""))

    async def receive_json(self) -> Any:
        """Receive and decode a JSON text message."""
        return json.loads(await self.receive_text())

    async def iter_json(self) -> AsyncIterator[Any]:
        """Yield JSON messages until the peer disconnects."""
        while True:
            try:
                yield await self.receive_json()
            except WebSocketDisconnect:
                return

    async def send_text(self, text: str) -> None:
        """Send a text message."""
        await self._send({"type": "websocket.send", "text": text})

    async def send_json(self, value: Any) -> None:
        """Send a JSON message."""
        await self.send_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")))

    async def join(self, room: str) -> None:
        """Join a named broadcast room."""
        if self.manager is None:
            return
        await self.manager.join(room, self)

    async def leave(self, room: str) -> None:
        """Leave a named broadcast room."""
        if self.manager is not None:
            await self.manager.leave(room, self)

    async def broadcast_json(self, room: str, value: Any) -> None:
        """Broadcast JSON to peers in a room."""
        if self.manager is not None:
            await self.manager.broadcast_json(room, value)
