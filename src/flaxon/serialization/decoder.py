from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Decoder(ABC):
    """Decoder implementation for the serialization subsystem."""

    @abstractmethod
    def decode(self, data: Any) -> Any:
        """Perform the decode operation for decoder."""
        pass


class DecoderChain:
    """Decoder chain implementation for the serialization subsystem."""

    def __init__(self, decoders: list[Decoder] | None = None) -> None:
        self.decoders = decoders or []

    def add(self, decoder: Decoder) -> DecoderChain:
        """Add the supplied item to this collection."""
        self.decoders.append(decoder)
        return self

    def decode(self, data: Any) -> Any:
        """Perform the decode operation for decoder chain."""
        result = data
        for decoder in self.decoders:
            result = decoder.decode(result)
        return result


class DecoderRegistry:
    """Decoder registry implementation for the serialization subsystem."""

    def __init__(self) -> None:
        self._decoders: dict[str, Decoder] = {}
        self._default_decoder: Decoder | None = None

    def register(self, name: str, decoder: Decoder) -> None:
        """Perform the register operation for decoder registry."""
        self._decoders[name] = decoder

    def get(self, name: str) -> Decoder | None:
        """Retrieve the requested value using this object's configured behavior."""
        return self._decoders.get(name)

    def set_default(self, decoder: Decoder) -> None:
        """Set the default."""
        self._default_decoder = decoder

    def decode(self, data: Any, name: str | None = None) -> Any:
        """Perform the decode operation for decoder registry."""
        if name and name in self._decoders:
            return self._decoders[name].decode(data)
        if self._default_decoder:
            return self._default_decoder.decode(data)
        raise ValueError("No decoder registered")
