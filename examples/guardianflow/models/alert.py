from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Alert:
    id: str
    type: str
    severity: str
    title: str
    explanation: str
    confidence: float
    timestamp: datetime
    camera_id: str
    related_event_ids: list[str] = field(default_factory=list)
    status: str = "new"

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["timestamp"] = self.timestamp.isoformat()
        return value
