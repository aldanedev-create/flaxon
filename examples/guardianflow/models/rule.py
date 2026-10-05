from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class Rule:
    name: str
    conditions: list[str]
    within_seconds: int = 120
    result_type: str = "activity"
    severity: str = "info"
    schedule: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
