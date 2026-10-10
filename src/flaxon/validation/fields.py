from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar

from .errors import FieldError
from .validators import Validator, required_validator

if TYPE_CHECKING:
    from .schema import Schema


class Field:
    """Validate and convert  field values."""

    def __init__(
        self,
        *,
        required: bool = False,
        default: Any = None,
        nullable: bool = False,
        validators: list[Validator] | None = None,
        description: str | None = None,
        examples: list[Any] | None = None,
    ) -> None:
        self.required = required
        self.default = default
        self.nullable = nullable
        self.validators = validators or []
        self.description = description
        self.examples = examples or []
        self.name = ""
        self._validators = []

        if required:
            self._validators.append(required_validator)

        if validators:
            self._validators.extend(validators)

    def bind(self, name: str) -> None:
        """Bind the supplied values to this object's context."""
        self.name = name

    def deserialize(self, value: Any) -> Any:
        """Restore a value from its serialized representation."""
        if value is None:
            if self.nullable:
                return None
            if self.required and self.default is None:
                raise FieldError("This field is required.")
            return self.default
        return value

    def validate(self, value: Any) -> None:
        """Check the supplied value against the configured constraints."""
        for validator in self._validators:
            validator(value, self)

    def serialize(self, value: Any) -> Any:
        """Convert the supplied value into its serialized representation."""
        return value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, required={self.required})"


class AnyField(Field):
    """Validate and convert any field values."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


class StrField(Field):
    """Validate and convert str field values."""

    def __init__(
        self,
        *,
        min_length: int | None = None,
        max_length: int | None = None,
        strip: bool = True,
        pattern: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.strip = strip
        self.pattern = pattern

    def deserialize(self, value: Any) -> str | None:
        """Restore a value from its serialized representation."""
        value = super().deserialize(value)
        if value is None:
            return None
        if not isinstance(value, str):
            raise FieldError("Expected a string.")
        value = value.strip() if self.strip else value
        if self.min_length is not None and len(value) < self.min_length:
            raise FieldError(f"Must contain at least {self.min_length} characters.")
        if self.max_length is not None and len(value) > self.max_length:
            raise FieldError(f"Must contain no more than {self.max_length} characters.")
        if self.pattern and not re.match(self.pattern, value):
            raise FieldError(f"Must match pattern: {self.pattern}")
        return value


class IntField(Field):
    """Validate and convert int field values."""

    def __init__(
        self,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.minimum = minimum
        self.maximum = maximum

    def deserialize(self, value: Any) -> int | None:
        """Restore a value from its serialized representation."""
        value = super().deserialize(value)
        if value is None:
            return None
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise FieldError("Expected an integer.") from exc
        if self.minimum is not None and number < self.minimum:
            raise FieldError(f"Must be at least {self.minimum}.")
        if self.maximum is not None and number > self.maximum:
            raise FieldError(f"Must be no greater than {self.maximum}.")
        return number


class FloatField(Field):
    """Validate and convert float field values."""

    def __init__(
        self,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.minimum = minimum
        self.maximum = maximum

    def deserialize(self, value: Any) -> float | None:
        """Restore a value from its serialized representation."""
        value = super().deserialize(value)
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise FieldError("Expected a number.") from exc
        if self.minimum is not None and number < self.minimum:
            raise FieldError(f"Must be at least {self.minimum}.")
        if self.maximum is not None and number > self.maximum:
            raise FieldError(f"Must be no greater than {self.maximum}.")
        return number


class BoolField(Field):
    """Validate and convert bool field values."""

    TRUE_VALUES: ClassVar[Any] = {True, "1", "true", "True", "yes", "on", "enabled"}
    FALSE_VALUES: ClassVar[Any] = {False, "0", "false", "False", "no", "off", "disabled"}

    def deserialize(self, value: Any) -> bool | None:
        """Restore a value from its serialized representation."""
        value = super().deserialize(value)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.lower().strip()
            if normalized in self.TRUE_VALUES:
                return True
            if normalized in self.FALSE_VALUES:
                return False
        raise FieldError("Expected a boolean value (true/false, yes/no, on/off, 1/0).")


class ChoiceField(Field):
    """Validate and convert choice field values."""

    def __init__(
        self,
        choices: list[Any] | tuple[Any, ...] | set[Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.choices = list(choices)

    def deserialize(self, value: Any) -> Any:
        """Restore a value from its serialized representation."""
        value = super().deserialize(value)
        if value is None:
            return None
        if value not in self.choices:
            values = ", ".join(map(str, sorted(self.choices, key=str)))
            raise FieldError(f"Choose one of: {values}.")
        return value


class EmailField(StrField):
    """Validate and convert email field values."""

    EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def deserialize(self, value: Any) -> str | None:
        """Restore a value from its serialized representation."""
        value = super().deserialize(value)
        if value is not None and not self.EMAIL_RE.match(value):
            raise FieldError("Enter a valid email address.")
        return value


class DateField(Field):
    """Validate and convert date field values."""

    def __init__(self, format: str = "%Y-%m-%d", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.format = format

    def deserialize(self, value: Any) -> date | None:
        """Restore a value from its serialized representation."""
        value = super().deserialize(value)
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.strptime(value, self.format).date()
            except ValueError as exc:
                raise FieldError(f"Expected date in format {self.format}.") from exc
        raise FieldError("Expected a date string or date object.")


class DateTimeField(Field):
    """Validate and convert date time field values."""

    def __init__(self, format: str = "%Y-%m-%dT%H:%M:%S", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.format = format

    def deserialize(self, value: Any) -> datetime | None:
        """Restore a value from its serialized representation."""
        value = super().deserialize(value)
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.strptime(value, self.format)
            except ValueError as exc:
                raise FieldError(f"Expected datetime in format {self.format}.") from exc
        raise FieldError("Expected a datetime string or datetime object.")


class DecimalField(Field):
    """Validate and convert decimal field values."""

    def __init__(
        self,
        *,
        minimum: Decimal | None = None,
        maximum: Decimal | None = None,
        places: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.minimum = minimum
        self.maximum = maximum
        self.places = places

    def deserialize(self, value: Any) -> Decimal | None:
        """Restore a value from its serialized representation."""
        value = super().deserialize(value)
        if value is None:
            return None
        try:
            decimal = Decimal(str(value))
        except (TypeError, ValueError) as exc:
            raise FieldError("Expected a decimal number.") from exc
        if self.minimum is not None and decimal < self.minimum:
            raise FieldError(f"Must be at least {self.minimum}.")
        if self.maximum is not None and decimal > self.maximum:
            raise FieldError(f"Must be no greater than {self.maximum}.")
        if self.places is not None and decimal.as_tuple().exponent < -self.places:
            raise FieldError(f"Must have at most {self.places} decimal places.")
        return decimal


class UUIDField(Field):
    """Validate and convert uuid field values."""

    def deserialize(self, value: Any) -> uuid.UUID | None:
        """Restore a value from its serialized representation."""
        value = super().deserialize(value)
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, str):
            try:
                return uuid.UUID(value)
            except ValueError as exc:
                raise FieldError("Expected a valid UUID.") from exc
        raise FieldError("Expected a UUID string or UUID object.")


class ListField(Field):
    """Validate and convert list field values."""

    def __init__(
        self,
        item_field: Field | None = None,
        *,
        min_items: int | None = None,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.item_field = item_field
        self.min_items = min_items
        self.max_items = max_items

    def deserialize(self, value: Any) -> list | None:
        """Restore a value from its serialized representation."""
        value = super().deserialize(value)
        if value is None:
            return None
        if not isinstance(value, list):
            raise FieldError("Expected a list.")
        if self.min_items is not None and len(value) < self.min_items:
            raise FieldError(f"Must contain at least {self.min_items} items.")
        if self.max_items is not None and len(value) > self.max_items:
            raise FieldError(f"Must contain no more than {self.max_items} items.")
        if self.item_field:
            result = []
            for idx, item in enumerate(value):
                try:
                    result.append(self.item_field.deserialize(item))
                except FieldError as exc:
                    raise FieldError(f"Item at index {idx}: {exc}") from exc
            return result
        return value


class NestedField(Field):
    """Validate and convert nested field values."""

    def __init__(self, schema_class: type[Schema], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.schema_class = schema_class

    def deserialize(self, value: Any) -> Schema | None:
        """Restore a value from its serialized representation."""
        value = super().deserialize(value)
        if value is None:
            return None
        if not isinstance(value, dict):
            raise FieldError("Expected an object.")
        return self.schema_class.load(value)
