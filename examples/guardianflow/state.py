from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

from .intelligence import Correlator, PolicySet
from .models import Alert, Camera, GuardianEvent, VisionFact
from .ring import RingClient
from .vision import VisionPipeline


class GuardianState:
    def __init__(self, policy_dir: str) -> None:
        self.ring = RingClient()
        self.vision = VisionPipeline()
        self.policies = PolicySet(policy_dir)
        self.correlator = Correlator(self.policies)
        self.events: deque[GuardianEvent] = deque(maxlen=100)
        self.facts: deque[VisionFact] = deque(maxlen=100)
        self.alerts: list[Alert] = []
        self.cameras = {"front-door": Camera("front-door", "Front door", "Porch")}
        self.manager: Any = None

    async def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        event = self.ring.normalize(payload)
        fact = self.vision.process(event)
        alert = self.correlator.process(event)
        self.events.append(event)
        self.facts.append(fact)
        camera = self.cameras.setdefault(event.camera_id, Camera(event.camera_id, event.camera_id.title(), "Unknown"))
        camera.status = "online"
        camera.last_event_at = event.timestamp
        if alert:
            self.alerts.insert(0, alert)
        await self.publish({"kind": "alert" if alert else "event", "event": event.to_dict(), "alert": alert.to_dict() if alert else None})
        return {"event": event.to_dict(), "fact": fact.to_dict(), "alert": alert.to_dict() if alert else None}

    async def publish(self, payload: dict[str, Any]) -> None:
        if self.manager is not None:
            await self.manager.broadcast_json("guardianflow", payload)

    def summary(self) -> dict[str, int]:
        return {"events": len(self.events), "alerts": len([item for item in self.alerts if item.status == "new"]), "cameras": len(self.cameras), "facts": len(self.facts)}

    def graph(self) -> list[dict[str, Any]]:
        return self.correlator.graph.snapshot()
