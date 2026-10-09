"""Case-conversion helpers for identifiers."""

from __future__ import annotations

import re

_ACRONYM_BOUNDARY_RE = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_BOUNDARY_RE = re.compile(r"([a-z0-9])([A-Z])")
_NON_ALNUM_RE = re.compile(r"[^0-9a-zA-Z]+")


def to_snake_case(value: str) -> str:
    """Convert any camelCase, PascalCase, kebab-case, or spaced string to snake_case."""
    value = _NON_ALNUM_RE.sub("_", value.strip())
    value = _ACRONYM_BOUNDARY_RE.sub(r"\1_\2", value)
    value = _CAMEL_BOUNDARY_RE.sub(r"\1_\2", value)
    return re.sub(r"_+", "_", value).strip("_").lower()


def camel_to_snake(value: str) -> str:
    """Convert a camelCase or PascalCase string to snake_case."""
    return to_snake_case(value)


def snake_to_camel(value: str, *, pascal: bool = False) -> str:
    """Convert a snake_case string to camelCase (or PascalCase if pascal=True)."""
    parts = [p for p in value.split("_") if p]
    if not parts:
        return ""
    if pascal:
        return "".join(p.capitalize() for p in parts)
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def to_kebab_case(value: str) -> str:
    """Convert any camelCase, PascalCase, snake_case, or spaced string to kebab-case."""
    return to_snake_case(value).replace("_", "-")
