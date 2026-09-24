"""Route definitions and path pattern compilation."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .converters import get_converter

_PARAMETER = re.compile(r"<(?:(?P<converter>[a-zA-Z_][a-zA-Z0-9_]*):)?(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)>")


def compile_path(path: str) -> tuple[re.Pattern[str], list[tuple[str, str]]]:
    """Compile a Flaxon path template into a matching regular expression."""
    parts: list[str] = []
    parameters: list[tuple[str, str]] = []
    position = 0
    for match in _PARAMETER.finditer(path):
        parts.append(re.escape(path[position : match.start()]))
        converter_name = match.group("converter") or "str"
        converter = get_converter(converter_name)
        name = match.group("name")
        parts.append(f"(?P<{name}>{converter.regex})")
        parameters.append((name, converter_name))
        position = match.end()
    parts.append(re.escape(path[position:]))
    return re.compile("^" + "".join(parts) + "$") , parameters


@dataclass
class Route:
    """A registered HTTP route."""

    path: str
    endpoint: Callable[..., Any]
    methods: set[str]
    name: str | None = None
    registration_order: int = 0
    summary: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    operation_id: str | None = None
    responses: dict[str | int, Any] | None = None
    deprecated: bool = False
    security: list[dict[str, list[str]]] | None = None

    def __post_init__(self) -> None:
        self.pattern, self.parameters = compile_path(self.path)

    @property
    def specificity(self) -> tuple[int, int, int]:
        """Rank literal routes ahead of parameterized routes."""
        segments = [segment for segment in self.path.strip("/").split("/") if segment]
        literal = sum(1 for segment in segments if not _PARAMETER.fullmatch(segment))
        parameters = len(segments) - literal
        return (literal, -parameters, len(segments))

    def match(self, path: str) -> dict[str, Any] | None:
        """Return typed parameters when the path matches."""
        matched = self.pattern.fullmatch(path)
        if not matched:
            return None
        values = matched.groupdict()
        return {name: get_converter(converter).cast(values[name]) for name, converter in self.parameters}


@dataclass
class WebSocketRoute:
    """A registered WebSocket route."""

    path: str
    endpoint: Callable[..., Any]
    name: str | None = None

    def __post_init__(self) -> None:
        self.pattern, self.parameters = compile_path(self.path)

    def match(self, path: str) -> dict[str, Any] | None:
        """Return typed parameters when the path matches."""
        matched = self.pattern.fullmatch(path)
        if not matched:
            return None
        values = matched.groupdict()
        return {name: get_converter(converter).cast(values[name]) for name, converter in self.parameters}
