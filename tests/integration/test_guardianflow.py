import asyncio
from datetime import datetime, timezone
from pathlib import Path

from examples.guardianflow.intelligence import PolicySet
from examples.guardianflow.models import GuardianEvent
from examples.guardianflow.ring import RingClient
from examples.guardianflow.state import GuardianState
from examples.guardianflow.vision import Detector


ROOT = Path(__file__).parents[2] / "examples" / "guardianflow"


def test_ring_payload_normalizes_and_detector_produces_fact():
    event = RingClient().normalize({"id": "1", "camera_id": "front-door", "type": "package_detected", "confidence": 1.4})
    fact = Detector().detect(event)
    assert event.confidence == 1.0
    assert fact.object_type == "package"


def test_delivery_then_removal_are_correlated():
    async def scenario():
        state = GuardianState(str(ROOT / "rules"))
        for event_type in ("person_detected", "package_detected", "person_left"):
            await state.ingest({"camera_id": "front-door", "type": event_type})
        assert state.alerts[0].type == "package_delivery"
        await state.ingest({"camera_id": "front-door", "type": "person_detected"})
        await state.ingest({"camera_id": "front-door", "type": "package_removed"})
        assert state.alerts[0].type == "package_removal"
        assert 0.0 <= state.alerts[0].confidence <= 1.0
    asyncio.run(scenario())


def test_after_hours_policy_creates_warning():
    async def scenario():
        state = GuardianState(str(ROOT / "rules"))
        await state.ingest({"camera_id": "front-door", "type": "person_detected", "timestamp": datetime(2026, 1, 1, 23, 15, tzinfo=timezone.utc).isoformat()})
        assert state.alerts[0].type == "after_hours_activity"
    asyncio.run(scenario())


def test_yaml_policy_matches_ordered_events():
    policies = PolicySet(str(ROOT / "rules"))
    now = datetime.now(timezone.utc)
    events = [GuardianEvent(str(i), "front-door", now, kind) for i, kind in enumerate(("person_detected", "package_detected", "person_left"))]
    assert policies.sequence_matches(events, policies.get("package_delivery"))
