from __future__ import annotations

from uuid import uuid4

from ..ai import explain
from ..models import Alert, GuardianEvent
from .event_graph import EventGraph
from .policies import PolicySet


class Correlator:
    def __init__(self, policies: PolicySet) -> None:
        self.policies = policies
        self.graph = EventGraph()
        self._emitted: set[tuple[str, str]] = set()

    def process(self, event: GuardianEvent) -> Alert | None:
        self.graph.add(event)
        events = self.graph.recent(event.camera_id)
        candidates = (
            ("package_delivery", "package_delivery"),
            ("package_removal", "package_removal"),
        )
        for policy_name, alert_type in candidates:
            matched = self.policies.sequence_matches(events, self.policies.get(policy_name))
            if matched:
                key = (policy_name, matched[-1].id)
                if key in self._emitted:
                    continue
                self._emitted.add(key)
                alert = self._alert(alert_type, matched, event)
                if alert_type == "package_delivery":
                    self.graph.add(GuardianEvent(
                        id=f"derived_{uuid4().hex[:8]}", camera_id=event.camera_id,
                        timestamp=event.timestamp, type="package_delivered", confidence=alert.confidence,
                    ))
                return alert
        after_hours = self.policies.get("after_hours")
        if event.type == "person_detected" and self.policies.after_hours(event.timestamp, after_hours):
            key = ("after_hours", event.id)
            if key not in self._emitted:
                self._emitted.add(key)
                return self._alert("after_hours_activity", [event], event)
        return None

    def _alert(self, alert_type: str, events: list[GuardianEvent], event: GuardianEvent) -> Alert:
        rule = self.policies.get("after_hours" if alert_type == "after_hours_activity" else alert_type)
        return Alert(
            id=f"alert_{uuid4().hex[:10]}", type=alert_type, severity=rule.severity,
            title={"package_delivery": "Package delivery confirmed", "package_removal": "Package removal detected", "after_hours_activity": "After-hours activity"}[alert_type],
            explanation=explain(alert_type), confidence=min(item.confidence for item in events),
            timestamp=event.timestamp, camera_id=event.camera_id,
            related_event_ids=[item.id for item in events],
        )
