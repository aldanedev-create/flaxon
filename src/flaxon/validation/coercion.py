from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any, TypeVar

T = TypeVar("T")


class Coercer:
    """Coercer implementation for the validation subsystem."""

    def __init__(self) -> None:
        self._coercers: dict[type, Callable[[Any], Any]] = {}

    def register(self, target_type: type, coerce_func: Callable[[Any], Any]) -> None:
        """Perform the register operation for coercer."""
        self._coercers[target_type] = coerce_func

    def coerce(self, value: Any, target_type: type[T]) -> T | None:
        """Perform the coerce operation for coercer."""
        if value is None:
            return None
        if target_type in self._coercers:
            return self._coercers[target_type](value)
        if isinstance(value, target_type):
            return value
        if hasattr(target_type, "__origin__"):
            return value
        return target_type(value)


_default_coercer = Coercer()


def coerce_str(value: Any) -> str:
    """Coerce the str."""
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8")
    return str(value)


def coerce_int(value: Any) -> int:
    """Coerce the int."""
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        value = value.strip()
        if value.lower() in {"true", "yes", "on"}:
            return 1
        if value.lower() in {"false", "no", "off"}:
            return 0
        return int(value)
    raise TypeError(f"Cannot coerce {type(value)} to int")


def coerce_float(value: Any) -> float:
    """Coerce the float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    raise TypeError(f"Cannot coerce {type(value)} to float")


def coerce_bool(value: Any) -> bool:
    """Coerce the bool."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return _coerce_bool_condition(value=value)
    return bool(value)


def _coerce_bool_condition(*, value):
    """Handle condition behavior for coerce bool."""
    normalized = value.lower().strip()
    if normalized in {"true", "1", "yes", "on", "enabled", "active"}:
        return True
    if normalized in {"false", "0", "no", "off", "disabled", "inactive"}:
        return False
    return bool(value)


def coerce_list(value: Any) -> list:
    """Coerce the list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    return [value]


def coerce_date(value: Any) -> date:
    """Coerce the date."""
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Invalid date format: {value}")
    raise TypeError(f"Cannot coerce {type(value)} to date")


def coerce_datetime(value: Any) -> datetime:
    """Coerce the datetime."""
    if value is None:
        return datetime.now()
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        raise ValueError(f"Invalid datetime format: {value}")
    raise TypeError(f"Cannot coerce {type(value)} to datetime")


def coerce_decimal(value: Any) -> Decimal:
    """Coerce the decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        return Decimal(value.strip())
    raise TypeError(f"Cannot coerce {type(value)} to Decimal")


def coerce_uuid(value: Any) -> uuid.UUID:
    """Coerce the uuid."""
    if value is None:
        return uuid.uuid4()
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        return uuid.UUID(value)
    raise TypeError(f"Cannot coerce {type(value)} to UUID")


_default_coercer.register(str, coerce_str)
_default_coercer.register(int, coerce_int)
_default_coercer.register(float, coerce_float)
_default_coercer.register(bool, coerce_bool)
_default_coercer.register(list, coerce_list)
_default_coercer.register(date, coerce_date)
_default_coercer.register(datetime, coerce_datetime)
_default_coercer.register(Decimal, coerce_decimal)
_default_coercer.register(uuid.UUID, coerce_uuid)


def coerce(value: Any, target_type: type[T]) -> T | None:
    """Perform the coerce operation for this subsystem."""
    return _default_coercer.coerce(value, target_type)
