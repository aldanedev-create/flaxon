from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from ..models import GuardianEvent


class RingClient:
    """Small boundary for Ring-shaped events; hardware integration is optional."""

    def normalize(self, payload: dict[str, Any]) -> GuardianEvent:
        value = payload.get("timestamp")
        timestamp = datetime.now(timezone.utc)
        if value:
            timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        return GuardianEvent(
            id=str(payload.get("id") or f"evt_{uuid4().hex[:10]}"),
            camera_id=str(payload.get("camera_id") or "front-door"),
            timestamp=timestamp,
            type=str(payload.get("type") or "motion_detected"),
            confidence=float(payload.get("confidence", 1.0)),
            metadata=dict(payload.get("metadata") or {}),
        )
