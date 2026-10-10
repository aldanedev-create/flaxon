from __future__ import annotations

import time
from typing import Any


class WebSocketSnapshot:
    """Web socket snapshot implementation for the debugging subsystem."""

    def __init__(self, connection_id: str, path: str) -> None:
        self.connection_id = connection_id
        self.path = path
        self.created_at = time.time()
        self.messages: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self._closed = False
        self._close_code: int | None = None
        self._close_reason: str = ""

    def add_message(self, direction: str, message: Any, size: int) -> None:
        """Add the message."""
        self.messages.append({
            "timestamp": time.time(),
            "direction": direction,
            "message": str(message)[:500],
            "size": size,
        })

        if len(self.messages) > 100:
            self.messages = self.messages[-100:]

    def add_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Add the event."""
        self.events.append({
            "timestamp": time.time(),
            "type": event_type,
            "data": data,
        })

    def mark_closed(self, code: int, reason: str = "") -> None:
        """Mark the closed."""
        self._closed = True
        self._close_code = code
        self._close_reason = reason
        self.add_event("close", {"code": code, "reason": reason})

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        return {
            "connection_id": self.connection_id,
            "path": self.path,
            "created_at": self.created_at,
            "closed": self._closed,
            "close_code": self._close_code,
            "close_reason": self._close_reason,
            "message_count": len(self.messages),
            "messages": self.messages[-20:],
            "events": self.events[-20:],
        }

    @classmethod
    def from_connection(cls, socket: Any) -> WebSocketSnapshot:
        """Construct from the connection."""
        connection_id = id(socket)
        path = getattr(socket, "path", "/")
        return cls(str(connection_id), path)


class WebSocketSnapshotCollector:
    """Web socket snapshot collector implementation for the debugging subsystem."""

    def __init__(self, max_snapshots: int = 100) -> None:
        self._snapshots: dict[str, WebSocketSnapshot] = {}
        self._max_snapshots = max_snapshots

    def get_or_create(self, connection_id: str, path: str) -> WebSocketSnapshot:
        """Retrieve an existing entry or create one from the supplied defaults."""
        if connection_id not in self._snapshots:
            if len(self._snapshots) >= self._max_snapshots:
                oldest = min(self._snapshots.keys(), key=lambda k: self._snapshots[k].created_at)
                self._snapshots.pop(oldest, None)
            self._snapshots[connection_id] = WebSocketSnapshot(connection_id, path)
        return self._snapshots[connection_id]

    def get(self, connection_id: str) -> WebSocketSnapshot | None:
        """Retrieve the requested value using this object's configured behavior."""
        return self._snapshots.get(connection_id)

    def remove(self, connection_id: str) -> None:
        """Perform the remove operation for web socket snapshot collector."""
        self._snapshots.pop(connection_id, None)

    def clear(self) -> None:
        """Remove the stored entries."""
        self._snapshots.clear()

    def get_all(self) -> list[WebSocketSnapshot]:
        """Return all matching stored entries."""
        return list(self._snapshots.values())

    def get_active(self) -> list[WebSocketSnapshot]:
        """Return the active."""
        return [s for s in self._snapshots.values() if not s._closed]

    def to_dict(self) -> list[dict[str, Any]]:
        """Return a dictionary representation of the current value."""
        return [s.to_dict() for s in self._snapshots.values()]
