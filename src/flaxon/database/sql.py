"""Compose raw SQL identifiers while keeping values in database parameters."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def identifier(value: str) -> str:
    """Validate a simple table or column identifier; never accept SQL expressions."""
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"Invalid SQL identifier: {value!r}")
    return value


@dataclass(frozen=True)
class Columns:
    """Render an explicitly validated list of column identifiers."""

    names: Iterable[str]

    def render(self) -> str:
        """Join validated column names for a statement's column list."""
        return ", ".join(identifier(name) for name in self.names)


@dataclass(frozen=True)
class Parameters:
    """Render numbered bind placeholders without interpolating values."""

    count: int
    start: int = 1

    def render(self) -> str:
        """Build a comma-separated sequence of numbered parameters."""
        if self.count < 0 or self.start < 1:
            raise ValueError("Invalid SQL parameter range")
        return ", ".join(f"${number}" for number in range(self.start, self.start + self.count))


@dataclass(frozen=True)
class Assignments:
    """Pair validated column names with numbered bind placeholders."""

    names: Iterable[str]
    start: int = 1

    def render(self) -> str:
        """Build update assignments; callers pass values separately to the driver."""
        if self.start < 1:
            raise ValueError("Invalid SQL parameter range")
        return ", ".join(
            f"{identifier(name)} = ${number}" for number, name in enumerate(self.names, self.start)
        )


def statement(template: str, **names: Any) -> str:
    """Fill an internal SQL template with validated identifiers and bind lists.

    Templates belong to framework code. Application values must be passed as
    separate database arguments, never supplied as template text or fragments.
    Identifier validation happens on every composition, including after a
    caller changes a backend's table_name attribute.
    """
    rendered = {
        key: value.render() if isinstance(value, (Columns, Parameters, Assignments)) else identifier(value)
        for key, value in names.items()
    }
    return template.format_map(rendered)
