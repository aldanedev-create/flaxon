"""
WebSocket message handling for Flaxon.

This module provides message types and utilities for WebSocket messages.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class MessageType(Enum):
    """WebSocket message types."""

    TEXT = "text"
    BINARY = "bytes"
    JSON = "json"
    PING = "ping"
    PONG = "pong"
    CLOSE = "close"


@dataclass
class Message:
    """
    WebSocket message.

    Attributes:
        type: The message type.
        data: The message data.
        raw: The raw message data.
    """

    type: MessageType
    data: Any = None
    raw: Any = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> Message:
        """
        Create a Message from a raw ASGI message.

        Args:
            raw: The raw message.

        Returns:
            A Message instance.
        """
        if raw["type"] in {"websocket.receive", "websocket.send"}:
            if "text" in raw and raw["text"] is not None:
                return cls(MessageType.TEXT, raw["text"], raw)
            if "bytes" in raw and raw["bytes"] is not None:
                return cls(MessageType.BINARY, raw["bytes"], raw)

        if raw["type"] == "websocket.disconnect":
            return cls(MessageType.CLOSE, raw.get("code", 1000), raw)

        if raw["type"] == "websocket.ping":
            return cls(MessageType.PING, raw.get("bytes", b""), raw)

        if raw["type"] == "websocket.pong":
            return cls(MessageType.PONG, raw.get("bytes", b""), raw)

        return cls(MessageType.TEXT, raw, raw)

    @property
    def is_text(self) -> bool:
        """Check if the message is text."""
        return self.type == MessageType.TEXT

    @property
    def is_binary(self) -> bool:
        """Check if the message is binary."""
        return self.type == MessageType.BINARY

    @property
    def is_json(self) -> bool:
        """Check if the message is JSON."""
        return self.type == MessageType.JSON

    @property
    def is_close(self) -> bool:
        """Check if the message is a close message."""
        return self.type == MessageType.CLOSE

    @property
    def is_ping(self) -> bool:
        """Check if the message is a ping."""
        return self.type == MessageType.PING

    @property
    def is_pong(self) -> bool:
        """Check if the message is a pong."""
        return self.type == MessageType.PONG

    def as_text(self) -> str:
        """Get the message as text."""
        if self.type == MessageType.TEXT:
            return self.data
        if self.type == MessageType.BINARY:
            return self.data.decode("utf-8")
        if self.type == MessageType.JSON:
            return json.dumps(self.data)
        raise ValueError(f"Cannot convert {self.type} to text")

    def as_bytes(self) -> bytes:
        """Get the message as bytes."""
        if self.type == MessageType.BINARY:
            return self.data
        if self.type == MessageType.TEXT:
            return self.data.encode("utf-8")
        if self.type == MessageType.JSON:
            return json.dumps(self.data).encode("utf-8")
        raise ValueError(f"Cannot convert {self.type} to bytes")

    def as_json(self) -> Any:
        """Get the message as JSON."""
        if self.type == MessageType.JSON:
            return self.data
        if self.type == MessageType.TEXT:
            return json.loads(self.data)
        raise ValueError(f"Cannot convert {self.type} to JSON")

    def __repr__(self) -> str:
        """Get a string representation of the message."""
        return f"Message(type={self.type.value}, data={self.data})"
