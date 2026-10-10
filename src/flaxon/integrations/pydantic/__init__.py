"""Optional Pydantic request and response integration.

Pydantic is imported lazily so importing Flaxon never requires the optional
dependency. Endpoint parameters annotated with ``BaseModel`` subclasses are
validated automatically when Pydantic is installed.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any, get_args

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


def prepare_response_adapter(annotation: Any) -> Any:
    """Prepare schema-bound output conversion only for Pydantic annotations."""
    if not isinstance(annotation, type) and not get_args(annotation):
        return None
    if not is_pydantic_model_type(annotation) and not any(
        prepare_response_adapter(arg) is not None for arg in get_args(annotation)
    ):
        return None
    pydantic = _pydantic_module()
    return pydantic.TypeAdapter(annotation) if pydantic is not None else None


def filter_response(adapter: Any, value: Any) -> Any:
    """Revalidate model instances and serialize using the declared output schema."""
    base_model = _base_model_type()

    def plain(item: Any) -> Any:
        if base_model is not None and isinstance(item, base_model):
            # Extract fields rather than invoke subclass serializers. Revalidation
            # must not accept an existing subclass instance unchanged.
            result = {}
            for name, info in type(item).model_fields.items():
                if hasattr(item, name):
                    key = info.validation_alias or info.alias or name
                    _set_validation_value(result, key, plain(getattr(item, name)))
            result.update(item.model_extra or {})
            return result
        if isinstance(item, dict):
            return {key: plain(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [plain(child) for child in item]
        return item

    validated = adapter.validate_python(plain(value), from_attributes=True)
    return adapter.dump_python(validated, mode="python")


def _set_validation_value(result: dict[str, Any], key: Any, value: Any) -> None:
    """Populate the model's validation alias, including choices and nested paths."""
    if hasattr(key, "choices"):
        key = key.choices[0]
    if not hasattr(key, "path"):
        result[key] = value
        return
    target: Any = result
    path = key.path
    for index, part in enumerate(path[:-1]):
        next_value: Any = [] if isinstance(path[index + 1], int) else {}
        if isinstance(target, list):
            while len(target) <= part:
                target.append(None)
            if target[part] is None:
                target[part] = next_value
        else:
            target.setdefault(part, next_value)
        target = target[part]
    if isinstance(target, list):
        while len(target) <= path[-1]:
            target.append(None)
    target[path[-1]] = value
