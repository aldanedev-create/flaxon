from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .decoder import Decoder
from .encoder import Encoder
from .types import SerializationError


class JSONEncoder(Encoder):
    """Jsonencoder implementation for the serialization subsystem."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def encode(self, data: Any) -> str:
        """Perform the encode operation for jsonencoder."""
        try:
            return json.dumps(
                data, default=self._default, ensure_ascii=False, separators=(",", ":"), **self.kwargs
            )
        except TypeError as exc:
            raise SerializationError(f"Failed to encode JSON: {exc}") from exc

    def _default(self, value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if hasattr(value, "__dataclass_fields__"):
            return {k: getattr(value, k) for k in value.__dataclass_fields__}
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class JSONDecoder(Decoder):
    """Jsondecoder implementation for the serialization subsystem."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def decode(self, data: str | bytes) -> Any:
        """Perform the decode operation for jsondecoder."""
        try:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return json.loads(data, **self.kwargs)
        except json.JSONDecodeError as exc:
            raise SerializationError(f"Failed to decode JSON: {exc}") from exc


def json_encoder() -> JSONEncoder:
    """Perform the json encoder operation for this subsystem."""
    return JSONEncoder()


def json_decoder() -> JSONDecoder:
    """Perform the json decoder operation for this subsystem."""
    return JSONDecoder()
