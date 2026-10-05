from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from ..models import GuardianEvent


class EventGraph:
    def __init__(self, limit: int = 80) -> None:
        self._events: dict[str, deque[GuardianEvent]] = defaultdict(lambda: deque(maxlen=limit))

    def add(self, event: GuardianEvent) -> None:
        self._events[event.camera_id].append(event)

    def recent(self, camera_id: str, seconds: int = 3600) -> list[GuardianEvent]:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        return [event for event in self._events[camera_id] if event.timestamp >= cutoff]

    def snapshot(self, camera_id: str = "front-door") -> list[dict]:
        return [event.to_dict() for event in self._events[camera_id]]
