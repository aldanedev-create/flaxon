from __future__ import annotations

import json
from typing import Any


class SessionSerializer:
    """Session serializer implementation for the sessions subsystem."""

    def __init__(self) -> None:
        self._encoders: dict[type, Any] = {}

    def encode(self, data: dict[str, Any]) -> str:
        """Perform the encode operation for session serializer."""
        return json.dumps(data, default=self._default, ensure_ascii=False, separators=(",", ":"))

    def decode(self, data: str) -> dict[str, Any]:
        """Perform the decode operation for session serializer."""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {}

    def _default(self, value: Any) -> Any:
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if hasattr(value, "__dataclass_fields__"):
            return {k: getattr(value, k) for k in value.__dataclass_fields__}
        raise TypeError(f"Object of type {type(value).__name__} is not serializable")

    def serialize_session(self, session: Any) -> str:
        """Perform the serialize session operation for session serializer."""
        return self.encode(session.to_dict())

    def deserialize_session(self, data: str) -> dict[str, Any]:
        """Perform the deserialize session operation for session serializer."""
        return self.decode(data)


_default_serializer = SessionSerializer()


def serialize_session(session: Any) -> str:
    """Perform the serialize session operation for this subsystem."""
    return _default_serializer.serialize_session(session)


def deserialize_session(data: str) -> dict[str, Any]:
    """Perform the deserialize session operation for this subsystem."""
    return _default_serializer.deserialize_session(data)
