from __future__ import annotations

from datetime import datetime, time
from pathlib import Path
from typing import Iterable

import yaml

from ..models import GuardianEvent, Rule


class PolicySet:
    def __init__(self, directory: str | Path) -> None:
        self.rules: dict[str, Rule] = {}
        for path in sorted(Path(directory).glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            result = data.get("result") or {}
            self.rules[str(data["name"])] = Rule(
                name=str(data["name"]),
                conditions=list(data.get("conditions") or []),
                within_seconds=int(data.get("within_seconds", 120)),
                result_type=str(result.get("type", data["name"])),
                severity=str(result.get("severity", "info")),
                schedule=data.get("schedule"),
            )

    def get(self, name: str) -> Rule:
        return self.rules[name]

    def sequence_matches(self, events: Iterable[GuardianEvent], rule: Rule) -> list[GuardianEvent] | None:
        ordered = list(events)
        found: list[GuardianEvent] = []
        position = 0
        for event in ordered:
            if position < len(rule.conditions) and event.type == rule.conditions[position]:
                found.append(event)
                position += 1
        if position != len(rule.conditions) or not found:
            return None
        if (found[-1].timestamp - found[0].timestamp).total_seconds() > rule.within_seconds:
            return None
        return found

    def after_hours(self, timestamp: datetime, rule: Rule) -> bool:
        if not rule.schedule:
            return False
        start = time.fromisoformat(str(rule.schedule["start"]))
        end = time.fromisoformat(str(rule.schedule["end"]))
        current = timestamp.timetz().replace(tzinfo=None)
        return current >= start or current < end if start > end else start <= current < end
