"""ASGI WebSocket connection wrapper."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

#: Close code for "the peer sent no status" (RFC 6455). Used when a disconnect carries no code.
NO_STATUS_RECEIVED = 1005
#: Close code for "received a data type this endpoint cannot accept" (for example binary instead of text).
UNSUPPORTED_DATA = 1003
#: Close code for "received data that is not consistent with its type" (for example invalid JSON).
INVALID_PAYLOAD = 1007
#: Close code for "try again later". Sent when the server is at its connection limit.
TRY_AGAIN_LATER = 1013


class WebSocketState(StrEnum):
    """Connection lifecycle state."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"

    def __str__(self) -> str:
        """Preserve the established Enum string representation."""
        return f"{type(self).__name__}.{self.name}"


class WebSocketDisconnectError(Exception):
    """Raised when a peer disconnects, or when sending to a connection that is already closed."""

    def __init__(self, code: int = NO_STATUS_RECEIVED, reason: str = "") -> None:
        super().__init__(code, reason)
        self.code = code
        self.reason = reason


# Preserve the established public exception import.
WebSocketDisconnect = WebSocketDisconnectError


class WebSocketDataError(ValueError):
    """Raised when a peer sends a frame the endpoint cannot accept.

    ``code`` is the WebSocket close code the application closes the connection with.
    """

    def __init__(self, message: str, code: int = UNSUPPORTED_DATA) -> None:
        super().__init__(message)
        self.code = code


class WebSocket:
    """A convenient interface over ASGI WebSocket messages."""

    def __init__(self, scope: dict[str, Any], receive: Any, send: Any, manager: Any = None) -> None:
        self.scope = scope
        self._receive = receive
        self._send = send
        self.manager = manager
        self.path_params: dict[str, Any] = {}
        self.state = WebSocketState.CONNECTING
        #: The close code the peer disconnected with, once it has disconnected.
        self.close_code: int | None = None
        #: Set by ``Heartbeat.start`` so ``"pong"`` replies are recorded instead of reaching your handler.
        self.heartbeat: Any = None

    async def accept(
        self,
        subprotocol: str | None = None,
        headers: list[tuple[bytes, bytes]] | None = None,
    ) -> None:
        """Consume the initial handshake message and accept the peer connection.

        If the manager is at its connection limit the handshake is rejected and
        :class:`WebSocketDisconnect` is raised.
        """
        message = await self._receive()
        if message.get("type") != "websocket.connect":
            kind = message.get("type")
            raise RuntimeError(f"Expected 'websocket.connect' as the first message, got {kind!r}")
        if self.manager is not None and not getattr(self.manager, "has_capacity", True):
            self.state = WebSocketState.DISCONNECTED
            await self._send({"type": "websocket.close", "code": TRY_AGAIN_LATER, "reason": "Server is full"})
            raise WebSocketDisconnect(TRY_AGAIN_LATER, "Server is full")
        accept: dict[str, Any] = {"type": "websocket.accept"}
        if subprotocol is not None:
            accept["subprotocol"] = subprotocol
        if headers:
            accept["headers"] = headers
        await self._send(accept)
        self.state = WebSocketState.CONNECTED
        if self.manager is not None:
            await self.manager.connect(self)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close the peer connection. Never raises because the peer is already gone."""
        was_open = self.state is not WebSocketState.DISCONNECTED
        self.state = WebSocketState.DISCONNECTED
        try:
            if was_open:
                await self._send({"type": "websocket.close", "code": code, "reason": reason})
        except Exception as exc:  # the peer may already be gone; the goal is to end up closed
            logger.debug("WebSocket close failed (%s)", type(exc).__name__)
        finally:
            if self.manager is not None:
                await self.manager.disconnect(self)

    async def receive(self) -> dict[str, Any]:
        """Receive the next ASGI message."""
        if self.state is WebSocketState.DISCONNECTED:
            raise WebSocketDisconnect(self.close_code or NO_STATUS_RECEIVED)
        while True:
            message: dict[str, Any] = await self._receive()
            if message.get("type") == "websocket.disconnect":
                self.state = WebSocketState.DISCONNECTED
                self.close_code = int(message.get("code") or NO_STATUS_RECEIVED)
                if self.manager is not None:
                    await self.manager.disconnect(self)
                raise WebSocketDisconnect(self.close_code, str(message.get("reason") or ""))
            if self.heartbeat is not None and message.get("text") == "pong":
                self.heartbeat.pong_received(self)
                continue  # a heartbeat reply is not for the application
            return message

    async def receive_text(self) -> str:
        """Receive a text message. Raises :class:`WebSocketDataError` for a binary frame."""
        message = await self.receive()
        if message.get("text") is None and message.get("bytes") is not None:
            raise WebSocketDataError("Expected a text frame but received a binary frame", UNSUPPORTED_DATA)
        return str(message.get("text") or "")

    async def receive_bytes(self) -> bytes:
        """Receive a binary message. Raises :class:`WebSocketDataError` for a text frame."""
        message = await self.receive()
        if message.get("bytes") is None and message.get("text") is not None:
            raise WebSocketDataError("Expected a binary frame but received a text frame", UNSUPPORTED_DATA)
        return bytes(message.get("bytes") or b"")

    async def receive_json(self) -> Any:
        """Receive and decode a JSON text message.

        Invalid JSON raises :class:`json.JSONDecodeError`, which the application reports to the peer
        as close code 1007 if the endpoint does not handle it.
        """
        value: Any = json.loads(await self.receive_text())
        return value

    async def iter_json(self) -> AsyncIterator[Any]:
        """Yield JSON messages until the peer disconnects."""
        while True:
            try:
                yield await self.receive_json()
            except WebSocketDisconnect:
                return

    def _ensure_open(self) -> None:
        if self.state is WebSocketState.DISCONNECTED:
            raise WebSocketDisconnect(self.close_code or NO_STATUS_RECEIVED, "Connection is closed")

    async def send_text(self, text: str) -> None:
        """Send a text message. Raises :class:`WebSocketDisconnect` if the connection is closed."""
        self._ensure_open()
        await self._send({"type": "websocket.send", "text": text})

    async def send_bytes(self, data: bytes) -> None:
        """Send a binary message. Raises :class:`WebSocketDisconnect` if the connection is closed."""
        self._ensure_open()
        await self._send({"type": "websocket.send", "bytes": data})

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
