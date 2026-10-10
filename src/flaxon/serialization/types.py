from __future__ import annotations

from typing import Any


class SerializationError(Exception):
    """Report a serialization failure."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class UnsupportedTypeError(SerializationError):
    """Report a unsupported type failure."""

    def __init__(self, type_name: str, message: str | None = None) -> None:
        msg = message or f"Unsupported type: {type_name}"
        super().__init__(msg)
        self.type_name = type_name


class Serializer:
    """Serializer implementation for the serialization subsystem."""

    def __init__(self, encoder: Any, decoder: Any, content_type: str = "application/json") -> None:
        self.encoder = encoder
        self.decoder = decoder
        self.content_type = content_type

    def serialize(self, data: Any) -> Any:
        """Convert the supplied value into its serialized representation."""
        return self.encoder.encode(data)

    def deserialize(self, data: Any) -> Any:
        """Restore a value from its serialized representation."""
        return self.decoder.decode(data)


class SerializerRegistry:
    """Serializer registry implementation for the serialization subsystem."""

    def __init__(self) -> None:
        self._serializers: dict[str, Serializer] = {}
        self._default: Serializer | None = None

    def register(self, name: str, serializer: Serializer) -> None:
        """Perform the register operation for serializer registry."""
        self._serializers[name] = serializer

    def get(self, name: str) -> Serializer | None:
        """Retrieve the requested value using this object's configured behavior."""
        return self._serializers.get(name)

    def set_default(self, serializer: Serializer) -> None:
        """Set the default."""
        self._default = serializer

    def serialize(self, data: Any, name: str | None = None) -> Any:
        """Convert the supplied value into its serialized representation."""
        if name and name in self._serializers:
            return self._serializers[name].serialize(data)
        if self._default:
            return self._default.serialize(data)
        raise ValueError("No serializer registered")

    def deserialize(self, data: Any, name: str | None = None) -> Any:
        """Restore a value from its serialized representation."""
        if name and name in self._serializers:
            return self._serializers[name].deserialize(data)
        if self._default:
            return self._default.deserialize(data)
        raise ValueError("No serializer registered")
