from __future__ import annotations

from typing import Any


class ValidationMessages:
    DEFAULT_MESSAGES = {
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
        message = self.messages.get(key, self.messages["unknown"])
        return message.format(**kwargs)

    def set(self, key: str, message: str) -> None:
        self.messages[key] = message

    def extend(self, messages: dict[str, str]) -> None:
        self.messages.update(messages)


_default_messages = ValidationMessages()


def get_message(key: str, **kwargs: Any) -> str:
    return _default_messages.get(key, **kwargs)


def set_message(key: str, message: str) -> None:
    _default_messages.set(key, message)


def extend_messages(messages: dict[str, str]) -> None:
    _default_messages.extend(messages)


class MessageMixin:

    def get_error_message(self, key: str, **kwargs: Any) -> str:
        return get_message(key, **kwargs)

    def set_error_message(self, key: str, message: str) -> None:
        set_message(key, message)
