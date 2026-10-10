from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any


def import_string(value: str) -> Any:
    """
    Import an object from a 'module:attribute' string.

    Args:
        value: String in the format 'module:attribute'

    Returns:
        The imported object

    Raises:
        ValueError: If the string format is invalid
        ImportError: If the module cannot be imported
        AttributeError: If the attribute does not exist

    Example:
        >>> app = import_string("app:app")
    """
    if ":" not in value:
        raise ValueError("Import string must use the form 'module:attribute'.")

    module_name, attribute = value.split(":", 1)

    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    module = importlib.import_module(module_name)
    return getattr(module, attribute)


def import_string_optional(value: str, default: Any = None) -> Any:
    """
    Import an object from a 'module:attribute' string, returning default on failure.

    Args:
        value: String in the format 'module:attribute'
        default: Default value to return on failure

    Returns:
        The imported object or default
    """
    try:
        return import_string(value)
    except (ImportError, AttributeError, ValueError):
        return default


def import_module(module_name: str) -> Any:
    """Import a module by name."""
    return importlib.import_module(module_name)
