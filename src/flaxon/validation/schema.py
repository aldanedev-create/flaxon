from __future__ import annotations

from typing import Any

from .errors import FieldError, ValidationError
from .fields import Field


class SchemaMeta(type):
    """Schema meta implementation for the validation subsystem."""

    def __new__(mcls, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> type:
        """Allocate an instance with the requested configuration."""
        inherited: dict[str, Field] = {}
        for base in bases:
            inherited.update(getattr(base, "__fields__", {}))
        declared = {key: value for key, value in namespace.items() if isinstance(value, Field)}
        for key in declared:
            namespace.pop(key)
        fields = {**inherited, **declared}
        for field_name, field in fields.items():
            field.bind(field_name)
        namespace["__fields__"] = fields
        return super().__new__(mcls, name, bases, namespace)


class Schema(metaclass=SchemaMeta):
    """Schema implementation for the validation subsystem."""

    __fields__: dict[str, Field]

    def __init__(self, **values: Any) -> None:
        for name, value in values.items():
            setattr(self, name, value)

    @classmethod
    def load(cls, data: Any) -> Schema:
        """Load the requested resource using the configured source."""
        if not isinstance(data, dict):
            raise ValidationError({"body": ["Expected a JSON object."]})
        errors: dict[str, list[str]] = {}
        values: dict[str, Any] = {}
        for name, field in cls.__fields__.items():
            try:
                values[name] = field.deserialize(data.get(name))
            except FieldError as exc:
                errors.setdefault(name, []).append(str(exc))
        if errors:
            raise ValidationError(errors)
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        return {name: getattr(self, name, None) for name in self.__fields__}

    def to_json(self) -> dict[str, Any]:
        """Convert to the json."""
        result = {}
        for name, field in self.__fields__.items():
            value = getattr(self, name, None)
            if hasattr(field, "serialize"):
                result[name] = field.serialize(value)
            elif hasattr(value, "to_dict"):
                result[name] = value.to_dict()
            elif hasattr(value, "isoformat"):
                result[name] = value.isoformat()
            else:
                result[name] = value
        return result

    def validate(self) -> None:
        """Check the supplied value against the configured constraints."""
        errors: dict[str, list[str]] = {}
        for name, field in self.__fields__.items():
            value = getattr(self, name, None)
            try:
                field.validate(value)
            except FieldError as exc:
                errors.setdefault(name, []).append(str(exc))
        if errors:
            raise ValidationError(errors)

    def __repr__(self) -> str:
        fields = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"{self.__class__.__name__}({fields})"
