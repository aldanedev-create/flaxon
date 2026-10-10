"""Read bounded source-map segments from trusted build artifacts."""

from __future__ import annotations

from typing import Any

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def source_position(mapping: dict[str, Any], line: int, column: int) -> tuple[str, int, int] | None:
    """Resolve a generated position using the nearest preceding mapped segment."""
    source = original_line = original_column = 0
    selected = None
    lines = str(mapping.get("mappings", "")).split(";")
    if line < 1 or line > len(lines):
        return None
    for row, segments in enumerate(lines[:line]):
        generated_column = 0
        for segment in segments.split(","):
            values = _decode_segment(segment)
            if not values:
                continue
            generated_column += values[0]
            if len(values) < 4:
                continue
            source += values[1]
            original_line += values[2]
            original_column += values[3]
            if row == line - 1 and generated_column <= column - 1:
                selected = source, original_line, original_column
    if selected is None or selected[0] < 0 or selected[0] >= len(mapping.get("sources", [])):
        return None
    return str(mapping["sources"][selected[0]]), selected[1] + 1, selected[2] + 1


def _decode_segment(segment: str) -> list[int]:
    values, value, shift = [], 0, 0
    for char in segment:
        digit = _ALPHABET.find(char)
        if digit < 0 or shift > 35:
            raise ValueError("Invalid source-map segment")
        value |= (digit & 31) << shift
        if digit & 32:
            shift += 5
        else:
            values.append(-(value >> 1) if value & 1 else value >> 1)
            value = shift = 0
    if shift:
        raise ValueError("Truncated source-map segment")
    return values
