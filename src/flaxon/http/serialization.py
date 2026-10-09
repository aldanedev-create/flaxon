"""Strict, browser-safe JSON with an explicit legacy migration mode."""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import math
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

import orjson

SAFE_INTEGER = (1 << 53) - 1


def legacy_default(value: Any) -> Any:
    """Retain the historical model_dump/str fallback for explicit legacy mode."""
    dump = getattr(value, 'model_dump', None)
    return dump() if callable(dump) else str(value)


def _normalize(value: Any, active: set[int] | None = None) -> Any:
    """Normalize exceptional values without mutating user data."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return str(value) if abs(value) > SAFE_INTEGER else value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('JSON numbers must be finite')
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError('JSON decimals must be finite')
        return str(value)
    if isinstance(value, dt.datetime):
        if value.utcoffset() is not None:
            return value.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
        return value.isoformat()
    if isinstance(value, (dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return _normalize(value.value, active)
    active = set() if active is None else active
    identity = id(value)
    if identity in active:
        raise TypeError('Circular JSON value')
    active.add(identity)
    try:
        if isinstance(value, dict):
            if any(not isinstance(key, str) for key in value):
                raise TypeError('JSON object keys must be strings')
            return {key: _normalize(item, active) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [_normalize(item, active) for item in value]
        dump = getattr(value, 'model_dump', None)
        if callable(dump):
            return _normalize(dump(), active)
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return {field.name: _normalize(getattr(value, field.name), active)
                    for field in dataclasses.fields(value)}
        raise TypeError(f'Unsupported JSON value: {type(value).__name__}')
    finally:
        active.remove(identity)


def _validate_finite(value: Any, active: set[int] | None = None) -> None:
    """orjson represents nonfinite floats as null; reject them before returning."""
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('JSON numbers must be finite')
    if isinstance(value, Enum):
        _validate_finite(value.value, active)
    elif isinstance(value, (dict, list, tuple)):
        active = set() if active is None else active
        if id(value) in active:
            raise TypeError('Circular JSON value')
        active.add(id(value))
        try:
            for item in value.values() if isinstance(value, dict) else value:
                _validate_finite(item, active)
        finally:
            active.remove(id(value))


def dumps(content: Any, *, legacy: bool = False) -> bytes:
    """Encode normal values directly; normalize only exceptional representations."""
    if legacy:
        return json.dumps(content, ensure_ascii=False, default=legacy_default).encode('utf-8')
    try:
        body = orjson.dumps(content, default=_normalize,
                            option=orjson.OPT_STRICT_INTEGER | orjson.OPT_PASSTHROUGH_DATETIME
                            | orjson.OPT_PASSTHROUGH_DATACLASS)
    except orjson.JSONEncodeError:
        body = orjson.dumps(_normalize(content))
    # A nonfinite native float can only appear as null. Ordinary responses avoid
    # walking their entire object tree; model/default values normalize beforehand.
    if b'null' in body:
        _validate_finite(content)
    return body
