"""Explicit request parameter declarations used by routing and OpenAPI."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .converters import CONVERTERS


MISSING = object()


class Parameter:
    """A named route parameter and its registered converter."""

    def __init__(self, name: str, type_name: str = "str") -> None:
        self.name = name
        self.type = type_name
        if type_name not in CONVERTERS:
            raise ValueError(f"Unknown parameter type: {type_name}")
        self.converter = CONVERTERS[type_name]

    def convert(self, value: str) -> Any:
        return self.converter.cast(value)

    def matches(self, value: str) -> bool:
        return bool(re.fullmatch(self.converter.regex, value))

    def __repr__(self) -> str:
        return f"Parameter({self.name}:{self.type})"


def parse_parameters(path: str) -> list[Parameter]:
    """Parse angle-bracket and brace-style route parameters."""
    parameters: list[Parameter] = []
    for match in re.finditer(
        r"<(?:(?P<type>[a-zA-Z_][a-zA-Z0-9_]*):)?(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)>",
        path,
    ):
        parameters.append(Parameter(match.group("name"), match.group("type") or "str"))
    for match in re.finditer(
        r"\{(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)(?::(?P<type>[a-zA-Z_][a-zA-Z0-9_]*))?\}",
        path,
    ):
        parameters.append(Parameter(match.group("name"), match.group("type") or "str"))
    return parameters


def extract_parameters(path: str, values: dict[str, str]) -> dict[str, Any]:
    """Convert extracted route values using the path converters."""
    return {
        parameter.name: parameter.convert(values[parameter.name])
        for parameter in parse_parameters(path)
        if parameter.name in values
    }


def validate_parameters(path: str, values: dict[str, str]) -> bool:
    """Return whether all declared route parameters are present and valid."""
    for parameter in parse_parameters(path):
        if parameter.name not in values or not parameter.matches(values[parameter.name]):
            return False
    return True


@dataclass(frozen=True)
class Query:
    """Declare a query-string parameter.

    ``Query()`` makes the parameter required.  ``Query(default)`` supplies a
    default while the remaining options describe validation and documentation
    metadata.  The marker is intentionally small and has no external
    dependency, so it can be used with native Python annotations.
    """

    default: Any = MISSING
    alias: str | None = None
    description: str | None = None
    ge: int | float | None = None
    le: int | float | None = None
    min_length: int | None = None
    max_length: int | None = None
    deprecated: bool = False


__all__ = ["MISSING", "Parameter", "Query", "extract_parameters", "parse_parameters", "validate_parameters"]
