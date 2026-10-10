"""Read ordinary pickle values without allowing arbitrary imported callables."""

from __future__ import annotations

import io
import pickle
from importlib import import_module
from typing import Any

_ALLOWED = {
    "builtins": {"set", "frozenset", "complex", "range", "bytearray"},
    "datetime": {"date", "datetime", "time", "timedelta", "timezone"},
    "decimal": {"Decimal"},
    "uuid": {"UUID"},
}


class _ValueUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> Any:
        if name not in _ALLOWED.get(module, set()):
            raise pickle.UnpicklingError(f"Unsupported pickle global: {module}.{name}")
        return getattr(import_module(module), name)


def load_value(data: bytes) -> Any:
    """Decode containers and allowlisted value classes, rejecting executable globals."""
    return _ValueUnpickler(io.BytesIO(data)).load()
