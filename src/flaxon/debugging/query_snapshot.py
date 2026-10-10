from __future__ import annotations

import time
from typing import Any


class QuerySnapshot:
    """Query snapshot implementation for the debugging subsystem."""

    def __init__(self, query: str, params: tuple | None = None, duration: float = 0) -> None:
        self.query = query
        self.params = params or ()
        self.duration = duration
        self.timestamp = time.time()
        self._result_preview = None

    def set_result_preview(self, result: Any, limit: int = 5) -> None:
        """Set the result preview."""
        if isinstance(result, list):
            self._result_preview = result[:limit]
        elif isinstance(result, dict):
            self._result_preview = dict(list(result.items())[:limit])
        else:
            self._result_preview = result

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        return {
            "timestamp": self.timestamp,
            "query": self.query,
            "params": self.params,
            "duration_ms": round(self.duration * 1000, 2),
            "result_preview": self._result_preview,
        }

    @classmethod
    def from_execution(cls, query: str, params: tuple | None = None, duration: float = 0) -> QuerySnapshot:
        """Construct from the execution."""
        return cls(query, params, duration)


class QuerySnapshotCollector:
    """Query snapshot collector implementation for the debugging subsystem."""

    def __init__(self, max_snapshots: int = 50) -> None:
        self._snapshots: list[QuerySnapshot] = []
        self._max_snapshots = max_snapshots

    def add(self, snapshot: QuerySnapshot) -> None:
        """Add the supplied item to this collection."""
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots :]

    def clear(self) -> None:
        """Remove the stored entries."""
        self._snapshots.clear()

    def get_all(self) -> list[QuerySnapshot]:
        """Return all matching stored entries."""
        return self._snapshots.copy()

    def get_slow_queries(self, threshold: float = 0.1) -> list[QuerySnapshot]:
        """Return the slow queries."""
        return [s for s in self._snapshots if s.duration > threshold]

    def get_recent(self, count: int = 10) -> list[QuerySnapshot]:
        """Return the recent."""
        return self._snapshots[-count:]

    def to_dict(self) -> list[dict[str, Any]]:
        """Return a dictionary representation of the current value."""
        return [s.to_dict() for s in self._snapshots]

    def __len__(self) -> int:
        return len(self._snapshots)

    def __iter__(self):
        return iter(self._snapshots)
