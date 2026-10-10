from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from .errors import FieldError


class Validator:
    """Validator implementation for the validation subsystem."""

    def __init__(self, func: Callable[[Any, Any], None], message: str | None = None) -> None:
        self.func = func
        self.message = message

    def __call__(self, value: Any, field: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        self.func(value, field, self.message)


def required_validator(value: Any, field: Any, message: str | None = None) -> None:
    """Build a validator for the configured required constraint."""
    if value is None:
        msg = message or "This field is required."
        raise FieldError(msg)


def length_validator(min_length: int | None = None, max_length: int | None = None) -> Validator:
    """Build a validator for the configured length constraint."""

    def _validator(value: Any, field: Any, message: str | None = None) -> None:
        if value is None:
            return
        if not hasattr(value, "__len__"):
            return
        length = len(value)
        if min_length is not None and length < min_length:
            msg = message or f"Must contain at least {min_length} items."
            raise FieldError(msg)
        if max_length is not None and length > max_length:
            msg = message or f"Must contain no more than {max_length} items."
            raise FieldError(msg)

    return Validator(_validator)


def min_validator(min_value: Any) -> Validator:
    """Build a validator for the configured min constraint."""

    def _validator(value: Any, field: Any, message: str | None = None) -> None:
        if value is None:
            return
        if value < min_value:
            msg = message or f"Must be at least {min_value}."
            raise FieldError(msg)

    return Validator(_validator)


def max_validator(max_value: Any) -> Validator:
    """Build a validator for the configured max constraint."""

    def _validator(value: Any, field: Any, message: str | None = None) -> None:
        if value is None:
            return
        if value > max_value:
            msg = message or f"Must be no greater than {max_value}."
            raise FieldError(msg)

    return Validator(_validator)


def range_validator(min_value: Any, max_value: Any) -> Validator:
    """Build a validator for the configured range constraint."""

    def _validator(value: Any, field: Any, message: str | None = None) -> None:
        if value is None:
            return
        if value < min_value or value > max_value:
            msg = message or f"Must be between {min_value} and {max_value}."
            raise FieldError(msg)

    return Validator(_validator)


def email_validator() -> Validator:
    """Build a validator for the configured email constraint."""
    email_re = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    def _validator(value: Any, field: Any, message: str | None = None) -> None:
        if value is None:
            return
        if not isinstance(value, str) or not email_re.match(value):
            msg = message or "Enter a valid email address."
            raise FieldError(msg)

    return Validator(_validator)


def url_validator() -> Validator:
    """Build a validator for the configured url constraint."""
    url_re = re.compile(
        r"^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?::\d+)?(?:/[-\w%_.~]*)*(?:\?[-\w%_.~=&]*)?(?:#[-\w%_.~]*)?$"
    )

    def _validator(value: Any, field: Any, message: str | None = None) -> None:
        if value is None:
            return
        if not isinstance(value, str) or not url_re.match(value):
            msg = message or "Enter a valid URL."
            raise FieldError(msg)

    return Validator(_validator)


def pattern_validator(pattern: str) -> Validator:
    """Build a validator for the configured pattern constraint."""
    compiled = re.compile(pattern)

    def _validator(value: Any, field: Any, message: str | None = None) -> None:
        if value is None:
            return
        if not isinstance(value, str) or not compiled.match(value):
            msg = message or f"Must match pattern: {pattern}"
            raise FieldError(msg)

    return Validator(_validator)


def and_validators(*validators: Validator) -> Validator:
    """Perform the and validators operation for this subsystem."""

    def _validator(value: Any, field: Any, message: str | None = None) -> None:
        for v in validators:
            try:
                v(value, field)
            except FieldError as exc:
                if message:
                    raise FieldError(message) from exc
                raise

    return Validator(_validator)


def or_validators(*validators: Validator) -> Validator:
    """Perform the or validators operation for this subsystem."""

    def _validator(value: Any, field: Any, message: str | None = None) -> None:
        errors = []
        for v in validators:
            try:
                v(value, field)
                return
            except FieldError as exc:
                errors.append(str(exc))
        msg = message or f"Failed all validators: {'; '.join(errors)}"
        raise FieldError(msg)

    return Validator(_validator)


def custom_validator(func: Callable[[Any, Any], None]) -> Validator:
    """Build a validator for the configured custom constraint."""

    def _validator(value: Any, field: Any, message: str | None = None) -> None:
        func(value, field)

    return Validator(_validator)
