from __future__ import annotations

from typing import Any, ClassVar


class ValidationMessages:
    """Validation messages implementation for the validation subsystem."""

    DEFAULT_MESSAGES: ClassVar[Any] = {
        "required": "This field is required.",
        "nullable": "This field cannot be null.",
        "type": "Expected type: {expected}, got: {actual}.",
        "min_length": "Must contain at least {min} characters.",
        "max_length": "Must contain no more than {max} characters.",
        "min_value": "Must be at least {min}.",
        "max_value": "Must be no greater than {max}.",
        "range": "Must be between {min} and {max}.",
        "email": "Enter a valid email address.",
        "url": "Enter a valid URL.",
        "pattern": "Must match pattern: {pattern}.",
        "choice": "Choose one of: {choices}.",
        "date": "Expected date in format {format}.",
        "datetime": "Expected datetime in format {format}.",
        "decimal": "Expected a decimal number.",
        "uuid": "Expected a valid UUID.",
        "list": "Expected a list.",
        "min_items": "Must contain at least {min} items.",
        "max_items": "Must contain no more than {max} items.",
        "nested": "Invalid nested object.",
        "unknown": "Invalid value.",
    }

    def __init__(self, custom_messages: dict[str, str] | None = None) -> None:
        self.messages = {**self.DEFAULT_MESSAGES, **(custom_messages or {})}

    def get(self, key: str, **kwargs: Any) -> str:
        """Retrieve the requested value using this object's configured behavior."""
        message = self.messages.get(key, self.messages["unknown"])
        return message.format(**kwargs)

    def set(self, key: str, message: str) -> None:
        """Store the supplied value under its key."""
        self.messages[key] = message

    def extend(self, messages: dict[str, str]) -> None:
        """Perform the extend operation for validation messages."""
        self.messages.update(messages)


_default_messages = ValidationMessages()


def get_message(key: str, **kwargs: Any) -> str:
    """Return the message."""
    return _default_messages.get(key, **kwargs)


def set_message(key: str, message: str) -> None:
    """Set the message."""
    _default_messages.set(key, message)


def extend_messages(messages: dict[str, str]) -> None:
    """Perform the extend messages operation for this subsystem."""
    _default_messages.extend(messages)


class MessageMixin:
    """Message mixin implementation for the validation subsystem."""

    def get_error_message(self, key: str, **kwargs: Any) -> str:
        """Return the error message."""
        return get_message(key, **kwargs)

    def set_error_message(self, key: str, message: str) -> None:
        """Set the error message."""
        set_message(key, message)
