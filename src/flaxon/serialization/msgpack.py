"""MessagePack serialization support for Flaxon."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .decoder import Decoder
from .encoder import Encoder
from .types import SerializationError


def _get_msgpack():
    """Lazy import for optional msgpack dependency."""
    try:
        import msgpack

        return msgpack
    except ImportError as exc:
        raise RuntimeError(
            "msgpack is required. Install with: pip install msgpack"
        ) from exc


class MsgPackEncoder(Encoder):
    """MessagePack encoder implementing the Encoder interface."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def encode(self, data: Any) -> bytes:
        """Encode data into MessagePack bytes."""
        msgpack = _get_msgpack()
        try:
            return msgpack.packb(data, default=self._default, **self.kwargs)
        except Exception as exc:
            raise SerializationError(f"Failed to encode MessagePack: {exc}") from exc

    def _default(self, value: Any) -> Any:
        """Fallback handling for custom non-standard types."""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if hasattr(value, "__dataclass_fields__"):
            return {k: getattr(value, k) for k in value.__dataclass_fields__}
        raise TypeError(
            f"Object of type {type(value).__name__} is not MessagePack serializable"
        )


class MsgPackDecoder(Decoder):
    """MessagePack decoder implementing the Decoder interface."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def decode(self, data: bytes) -> Any:
        """Decode MessagePack bytes back into Python objects."""
        msgpack = _get_msgpack()
        try:
            return msgpack.unpackb(data, **self.kwargs)
        except Exception as exc:
            raise SerializationError(f"Failed to decode MessagePack: {exc}") from exc


def msgpack_encoder(**kwargs: Any) -> MsgPackEncoder:
    """Factory helper to instantiate a MsgPackEncoder."""
    return MsgPackEncoder(**kwargs)


def msgpack_decoder(**kwargs: Any) -> MsgPackDecoder:
    """Factory helper to instantiate a MsgPackDecoder."""
    return MsgPackDecoder(**kwargs)
