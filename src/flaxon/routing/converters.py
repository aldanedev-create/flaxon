"""
Route parameter converters for Flaxon.

This module provides converters for route parameters that convert
string values from URLs to Python types.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Converter:
    """
    Route parameter converter.

    Attributes:
        regex: The regex pattern to match the parameter.
        cast: Function to convert the string to the target type.
    """

    regex: str
    cast: Callable[[str], Any]


CONVERTERS: dict[str, Converter] = {
    "str": Converter(r"[^/]+", str),
    "int": Converter(r"-?\d+", int),
    "float": Converter(r"-?(?:\d+(?:\.\d*)?|\.\d+)", float),
    "path": Converter(r".+", str),
    "uuid": Converter(r"[0-9a-fA-F-]{36}", uuid.UUID),
    "slug": Converter(r"[a-zA-Z0-9_-]+", str),
    "string": Converter(r"[^/]+", str),
    "integer": Converter(r"-?\d+", int),
}


def get_converter(name: str) -> Converter:
    """
    Get a converter by name.

    Args:
        name: The converter name.

    Returns:
        The Converter object.

    Raises:
        ValueError: If the converter is not found.
    """
    if name not in CONVERTERS:
        raise ValueError(f"Unknown converter: {name}")
    return CONVERTERS[name]


def register_converter(name: str, converter: Converter) -> None:
    """
    Register a custom converter.

    Args:
        name: The converter name.
        converter: The Converter object.
    """
    CONVERTERS[name] = converter


def has_converter(name: str) -> bool:
    """
    Check if a converter exists.

    Args:
        name: The converter name.

    Returns:
        True if the converter exists, False otherwise.
    """
    return name in CONVERTERS


def get_converter_names() -> list[str]:
    """
    Get all registered converter names.

    Returns:
        A list of converter names.
    """
    return list(CONVERTERS.keys())
