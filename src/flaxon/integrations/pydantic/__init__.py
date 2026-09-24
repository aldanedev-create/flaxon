"""Optional Pydantic request and response integration.

Pydantic is imported lazily so importing Flaxon never requires the optional
dependency. Endpoint parameters annotated with ``BaseModel`` subclasses are
validated automatically when Pydantic is installed.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any

from flaxon.validation import ValidationError


def _pydantic_module() -> ModuleType | None:
    """Return the optional Pydantic module without importing it eagerly."""
    try:
        return import_module("pydantic")
    except ImportError:
        return None


def _base_model_type() -> type[Any] | None:
    pydantic = _pydantic_module()
    return getattr(pydantic, "BaseModel", None) if pydantic is not None else None


def is_pydantic_model_type(annotation: Any) -> bool:
    """Return whether an annotation is a Pydantic model class."""
    base_model = _base_model_type()
    if base_model is None or not isinstance(annotation, type):
        return False
    return issubclass(annotation, base_model)


def load_pydantic_model(annotation: type[Any], value: Any) -> Any:
    """Validate request data with a Pydantic model and normalize its errors."""
    pydantic = _pydantic_module()
    if pydantic is None:
        raise RuntimeError(
            "Pydantic model validation requires the optional dependency. "
            "Install it with 'pip install flaxon[pydantic]'."
        )
    pydantic_validation_error = pydantic.ValidationError

    try:
        return annotation.model_validate(value)
    except pydantic_validation_error as exc:
        fields: dict[str, list[str]] = {}
        for item in exc.errors():
            location = ".".join(str(part) for part in item.get("loc", ())) or "body"
            fields.setdefault(location, []).append(str(item.get("msg", "Invalid value.")))
        raise ValidationError(fields) from exc


def dump_pydantic_model(value: Any) -> Any:
    """Return JSON-ready data for a Pydantic model or pass other values through."""
    model_dump = getattr(value, "model_dump", None)
    return model_dump() if callable(model_dump) else value


__all__ = [
    "dump_pydantic_model",
    "is_pydantic_model_type",
    "load_pydantic_model",
]
