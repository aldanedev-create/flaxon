from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Encoder(ABC):
    """Encoder implementation for the serialization subsystem."""

    @abstractmethod
    def encode(self, data: Any) -> Any:
        """Perform the encode operation for encoder."""
        pass


class EncoderChain:
    """Encoder chain implementation for the serialization subsystem."""

    def __init__(self, encoders: list[Encoder] | None = None) -> None:
        self.encoders = encoders or []

    def add(self, encoder: Encoder) -> EncoderChain:
        """Add the supplied item to this collection."""
        self.encoders.append(encoder)
        return self

    def encode(self, data: Any) -> Any:
        """Perform the encode operation for encoder chain."""
        result = data
        for encoder in self.encoders:
            result = encoder.encode(result)
        return result


class EncoderRegistry:
    """Encoder registry implementation for the serialization subsystem."""

    def __init__(self) -> None:
        self._encoders: dict[str, Encoder] = {}
        self._default_encoder: Encoder | None = None

    def register(self, name: str, encoder: Encoder) -> None:
        """Perform the register operation for encoder registry."""
        self._encoders[name] = encoder

    def get(self, name: str) -> Encoder | None:
        """Retrieve the requested value using this object's configured behavior."""
        return self._encoders.get(name)

    def set_default(self, encoder: Encoder) -> None:
        """Set the default."""
        self._default_encoder = encoder

    def encode(self, data: Any, name: str | None = None) -> Any:
        """Perform the encode operation for encoder registry."""
        if name and name in self._encoders:
            return self._encoders[name].encode(data)
        if self._default_encoder:
            return self._default_encoder.encode(data)
        raise ValueError("No encoder registered")
