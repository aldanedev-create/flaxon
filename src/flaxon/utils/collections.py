from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def unique(items: list[T]) -> list[T]:
    """Return a list with duplicate items removed, preserving order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def flatten(items: list[Any]) -> list[Any]:
    """Flatten a nested list."""
    result = []
    for item in items:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def group_by(items: list[T], key_func: Callable[[T], K]) -> dict[K, list[T]]:
    """Group items by a key function."""
    result: dict[K, list[T]] = {}
    for item in items:
        key = key_func(item)
        if key not in result:
            result[key] = []
        result[key].append(item)
    return result


def chunk_list(items: list[T], size: int) -> list[list[T]]:
    """Split a list into chunks of a given size."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def merge_dicts(*dicts: dict[K, V]) -> dict[K, V]:
    """Merge multiple dictionaries."""
    result: dict[K, V] = {}
    for d in dicts:
        result.update(d)
    return result


def get_path(data: dict[str, Any], path: str, default: Any = None) -> Any:
    """Get a value from a nested dictionary using a dot-separated path."""
    parts = path.split(".")
    current = data

    for part in parts:
        if not isinstance(current, dict):
            return default
        if part not in current:
            return default
        current = current[part]

    return current


def set_path(data: dict[str, Any], path: str, value: Any) -> None:
    """Set a value in a nested dictionary using a dot-separated path."""
    parts = path.split(".")
    current = data

    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    current[parts[-1]] = value


def omit(data: dict[K, V], *keys: K) -> dict[K, V]:
    """Return a dictionary with the specified keys omitted."""
    result = dict(data)
    for key in keys:
        result.pop(key, None)
    return result


def pick(data: dict[K, V], *keys: K) -> dict[K, V]:
    """Return a dictionary with only the specified keys."""
    return {key: data[key] for key in keys if key in data}
