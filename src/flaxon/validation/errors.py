from __future__ import annotations

from flaxon.exceptions import HTTPException


class ValidationError(HTTPException):
    """Report a validation failure."""

    def __init__(self, fields: dict[str, list[str]]) -> None:
        super().__init__(
            422,
            "Request validation failed.",
            code="FX-VAL-001",
            extra={"fields": fields},
        )
        self.fields = fields


class FieldError(ValueError):
    """Report a field failure."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class SchemaError(Exception):
    """Report a schema failure."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class CoercionError(Exception):
    """Report a coercion failure."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class ValidationConfigurationError(Exception):
    """Report a validation configuration failure."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message
