from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TaskResult:
    """A task status, result, error, and timing snapshot."""

    id: str
    name: str
    status: Any
    result: Any = None
    error: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0

    def is_pending(self) -> bool:
        """Return whether the recorded status is pending."""
        return self.status == "pending"

    def is_running(self) -> bool:
        """Return whether the recorded status is running."""
        return self.status == "running"

    def is_completed(self) -> bool:
        """Return whether the recorded status is completed."""
        return self.status == "completed"

    def is_failed(self) -> bool:
        """Return whether the recorded status is failed."""
        return self.status == "failed"

    def is_retry(self) -> bool:
        """Return whether the recorded status indicates a retry."""
        return self.status == "retry"

    def is_cancelled(self) -> bool:
        """Return whether the recorded status is cancelled."""
        return self.status == "cancelled"

    def is_timeout(self) -> bool:
        """Return whether the recorded status indicates a timeout."""
        return self.status == "timeout"

    def is_done(self) -> bool:
        """Return whether the task has reached a terminal state."""
        return self.status in {"completed", "failed", "cancelled", "timeout"}

    def get_duration(self) -> float | None:
        """Return elapsed execution seconds when both timestamps are available."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict[str, Any]:
        """Return result metadata with ISO timestamps and the computed duration."""
        return {
            "id": self.id,
            "name": self.name,
            "status": str(self.status),
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "duration": self.get_duration(),
        }
