from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


class Serializer:
    """Serializer implementation for the validation subsystem."""

    def __init__(self) -> None:
        self._serializers: dict[type, Callable[[Any], Any]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(str, lambda v: v)
        self.register(int, lambda v: v)
        self.register(float, lambda v: v)
        self.register(bool, lambda v: v)
        self.register(list, lambda v: [self.serialize(item) for item in v])
        self.register(dict, lambda v: {k: self.serialize(v) for k, v in v.items()})
        self.register(date, lambda v: v.isoformat())
        self.register(datetime, lambda v: v.isoformat())
        self.register(Decimal, float)
        self.register(Enum, lambda v: v.value)

    def register(self, type_: type, serializer: Callable[[Any], Any]) -> None:
        """Perform the register operation for serializer."""
        self._serializers[type_] = serializer

    def serialize(self, value: Any) -> Any:
        """Convert the supplied value into its serialized representation."""
        if value is None:
            return None

        value_type = type(value)

        if value_type in self._serializers:
            return self._serializers[value_type](value)

        for method in ("to_dict", "to_json", "model_dump"):
            if hasattr(value, method):
                return getattr(value, method)()
        if isinstance(value, (list, tuple, dict)):
            return self._serialize_container(value)
        if hasattr(value, "__dataclass_fields__"):
            return {key: self.serialize(getattr(value, key)) for key in value.__dataclass_fields__}
        return self._serialize_registered_subclass(value)

    def _serialize_container(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self.serialize(item) for key, item in value.items()}
        return [self.serialize(item) for item in value]

    def _serialize_registered_subclass(self, value: Any) -> Any:
        for value_type, serializer in self._serializers.items():
            if isinstance(value, value_type):
                return serializer(value)
        return value

    def to_json(self, value: Any) -> str:
        """Convert to the json."""
        return json.dumps(self.serialize(value), ensure_ascii=False, separators=(",", ":"))

    def to_json_pretty(self, value: Any, indent: int = 2) -> str:
        """Convert to the json pretty."""
        return json.dumps(self.serialize(value), ensure_ascii=False, indent=indent)


_default_serializer = Serializer()


def serialize(value: Any) -> Any:
    """Convert the supplied value into its serialized representation."""
    return _default_serializer.serialize(value)


def to_json(value: Any) -> str:
    """Convert to the json."""
    return _default_serializer.to_json(value)


def to_json_pretty(value: Any, indent: int = 2) -> str:
    """Convert to the json pretty."""
    return _default_serializer.to_json_pretty(value, indent)


def register_serializer(type_: type, serializer: Callable[[Any], Any]) -> None:
    """Register the serializer."""
    _default_serializer.register(type_, serializer)


class SerializerMixin:
    """Serializer mixin implementation for the validation subsystem."""

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith("_"):
                result[key] = serialize(value)
        return result

    def to_json(self) -> str:
        """Convert to the json."""
        return to_json(self.to_dict())

    def to_json_pretty(self, indent: int = 2) -> str:
        """Convert to the json pretty."""
        return to_json_pretty(self.to_dict(), indent)
