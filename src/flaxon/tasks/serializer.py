from __future__ import annotations

import json
import pickle
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any


class Serializer:
    """Convert task values and encode JSON or trusted pickle payloads."""

    def __init__(self) -> None:
        self._serializers: dict[type, Callable[[Any], Any]] = {}
        self._deserializers: dict[type, Callable[[Any], Any]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(str, lambda v: v, lambda v: v)
        self.register(int, lambda v: v, lambda v: v)
        self.register(float, lambda v: v, lambda v: v)
        self.register(bool, lambda v: v, lambda v: v)
        self.register(
            list,
            lambda v: [self.serialize(item) for item in v],
            lambda v: [self.deserialize(item) for item in v],
        )
        self.register(
            dict,
            lambda v: {k: self.serialize(v) for k, v in v.items()},
            lambda v: {k: self.deserialize(v) for k, v in v.items()},
        )
        self.register(datetime, lambda v: v.isoformat(), lambda v: datetime.fromisoformat(v))
        self.register(date, lambda v: v.isoformat(), lambda v: date.fromisoformat(v))
        self.register(Decimal, lambda v: float(v), lambda v: Decimal(str(v)))

    def register(
        self, type_: type, serializer: Callable[[Any], Any], deserializer: Callable[[Any], Any]
    ) -> None:
        """Register an encoder and decoder for a Python value type."""
        self._serializers[type_] = serializer
        self._deserializers[type_] = deserializer

    def serialize(self, value: Any) -> Any:
        """Recursively convert registered types and container values for storage."""
        if value is None:
            return None

        value_type = type(value)

        if value_type in self._serializers:
            return self._serializers[value_type](value)

        if isinstance(value, (list, tuple)):
            return [self.serialize(item) for item in value]

        if isinstance(value, dict):
            return {k: self.serialize(v) for k, v in value.items()}

        return value

    def deserialize(self, value: Any) -> Any:
        """Recursively decode container values using the registered conversions."""
        if value is None:
            return None

        if isinstance(value, (list, tuple)):
            return [self.deserialize(item) for item in value]

        if isinstance(value, dict):
            return {k: self.deserialize(v) for k, v in value.items()}

        for type_, deserializer in self._deserializers.items():
            try:
                return deserializer(value)
            except (ValueError, TypeError):
                continue

        return value

    def to_json(self, value: Any) -> str:
        """Serialize a value as a JSON string."""
        return json.dumps(self.serialize(value), default=str, ensure_ascii=False)

    def from_json(self, data: str) -> Any:
        """Parse JSON and recursively deserialize its values."""
        return self.deserialize(json.loads(data))

    def to_pickle(self, value: Any) -> bytes:
        """Encode a Python value using pickle for trusted internal storage."""
        return pickle.dumps(value)

    def from_pickle(self, data: bytes) -> Any:
        """Load a pickle payload; the input must come from a trusted source."""
        return pickle.loads(data)


_default_serializer = Serializer()


def serialize(value: Any) -> Any:
    """Recursively convert registered types and container values for storage."""
    return _default_serializer.serialize(value)


def deserialize(value: Any) -> Any:
    """Recursively decode container values using the registered conversions."""
    return _default_serializer.deserialize(value)


def to_json(value: Any) -> str:
    """Serialize a value as a JSON string."""
    return _default_serializer.to_json(value)


def from_json(data: str) -> Any:
    """Parse JSON and recursively deserialize its values."""
    return _default_serializer.from_json(data)


def to_pickle(value: Any) -> bytes:
    """Encode a Python value using pickle for trusted internal storage."""
    return _default_serializer.to_pickle(value)


def from_pickle(data: bytes) -> Any:
    """Load a pickle payload; the input must come from a trusted source."""
    return _default_serializer.from_pickle(data)
