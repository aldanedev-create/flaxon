from __future__ import annotations

import datetime
import decimal
import json
from typing import Any

from .types import Scalar


class ID(Scalar):
    def __init__(self) -> None:
        super().__init__("ID", "The `ID` scalar type represents a unique identifier.")

    def serialize(self, value: Any) -> str:
        return str(value)


class DateTime(Scalar):
    def __init__(self) -> None:
        super().__init__("DateTime", "The `DateTime` scalar type represents a date and time.")

    def serialize(self, value: Any) -> str:
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        return str(value)

    def parse_value(self, value: Any) -> datetime.datetime:
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, str):
            return datetime.datetime.fromisoformat(value)
        raise ValueError(f"Invalid DateTime: {value}")


class Decimal(Scalar):
    def __init__(self) -> None:
        super().__init__("Decimal", "The `Decimal` scalar type represents a decimal number.")

    def serialize(self, value: Any) -> str:
        if isinstance(value, decimal.Decimal):
            return str(value)
        return str(value)

    def parse_value(self, value: Any) -> decimal.Decimal:
        if isinstance(value, decimal.Decimal):
            return value
        try:
            return decimal.Decimal(str(value))
        except Exception as exc:
            raise ValueError(f"Invalid Decimal: {value}") from exc


class JSON(Scalar):
    def __init__(self) -> None:
        super().__init__("JSON", "The `JSON` scalar type represents a JSON object.")

    def serialize(self, value: Any) -> Any:
        return value

    def parse_value(self, value: Any) -> Any:
        return value

    def parse_literal(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value


class UUID(Scalar):
    def __init__(self) -> None:
        super().__init__("UUID", "The `UUID` scalar type represents a UUID.")

    def serialize(self, value: Any) -> str:
        return str(value)

    def parse_value(self, value: Any) -> Any:
        import uuid
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, str):
            return uuid.UUID(value)
        raise ValueError(f"Invalid UUID: {value}")


class URL(Scalar):
    def __init__(self) -> None:
        super().__init__("URL", "The `URL` scalar type represents a URL.")

    def serialize(self, value: Any) -> str:
        return str(value)


class Email(Scalar):
    def __init__(self) -> None:
        super().__init__("Email", "The `Email` scalar type represents an email address.")

    def serialize(self, value: Any) -> str:
        return str(value)
