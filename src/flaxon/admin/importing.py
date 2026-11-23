"""Import/export helpers: column mapping, size caps and CSV injection safety.

CSV cells beginning with ``= + - @`` (or tab/CR) are interpreted as formulas by
spreadsheet applications. Exporting user-controlled text verbatim is a
well-known injection vector, so every exported cell passes through
:func:`csv_safe`, which prefixes a single quote to neutralise the formula
without changing how the value reads.
"""

from __future__ import annotations

import json
from typing import Any

__all__ = ["csv_safe", "enforce_limits", "map_columns", "parse_mapping"]

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value: Any) -> str:
    """Return ``value`` as text that cannot start a spreadsheet formula."""
    text = "" if value is None else str(value)
    return "'" + text if text.lstrip()[:1] in _FORMULA_PREFIXES else text


def parse_mapping(raw: Any) -> dict[str, str]:
    """Parse a JSON object mapping source columns to model fields."""
    if raw in (None, "", {}):
        return {}
    if isinstance(raw, dict):
        mapping = raw
    else:
        try:
            mapping = json.loads(str(raw))
        except (TypeError, ValueError) as exc:
            raise ValueError("mapping must be a JSON object of column -> field") from exc
    if not isinstance(mapping, dict):
        raise ValueError("mapping must be a JSON object of column -> field")
    return {str(key): str(value) for key, value in mapping.items()}


def map_columns(
    rows: list[Any], mapping: dict[str, str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Rename source columns to model fields, preserving row order and values."""
    if not mapping:
        return [dict(row) for row in rows], []
    mapped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            errors.append({"row": index, "error": "Record must be an object."})
            continue
        target: dict[str, Any] = {}
        for column, field in mapping.items():
            if column in row:
                target[field] = row[column]
        mapped.append(target)
    return mapped, errors


def enforce_limits(*, payload_bytes: int, row_count: int, max_bytes: int, max_rows: int) -> None:
    """Raise ``ValueError`` when an import exceeds its configured caps."""
    if max_bytes and payload_bytes > max_bytes:
        raise ValueError(f"Import payload is too large ({payload_bytes} bytes > {max_bytes} bytes)")
    if max_rows and row_count > max_rows:
        raise ValueError(f"Import has too many rows ({row_count} > {max_rows})")
