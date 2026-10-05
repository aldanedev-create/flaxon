from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable


class RingSimulator:
    def __init__(self, delay: float = 0.12) -> None:
        self.delay = delay

    async def run(self, scenario: str, emit: Callable[[dict[str, Any]], Awaitable[Any]]) -> None:
        now = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
        sequences = {
            "package_delivery": ["person_detected", "package_detected", "person_left"],
            "package_removal": ["package_delivered", "person_detected", "package_removed"],
            "after_hours": ["person_detected"],
        }
        if scenario not in sequences:
            raise ValueError(f"Unknown demo scenario: {scenario}")
        for index, event_type in enumerate(sequences[scenario], start=1):
            timestamp = now + timedelta(seconds=index)
            if scenario == "after_hours":
                timestamp = timestamp.replace(hour=23, minute=15)
            await emit({
                "id": f"demo_{scenario}_{index}",
                "camera_id": "front-door",
                "timestamp": timestamp.isoformat(),
                "type": event_type,
                "confidence": 0.96 if event_type == "person_detected" else 0.92,
            })
            await asyncio.sleep(self.delay)
