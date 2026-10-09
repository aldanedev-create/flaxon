from __future__ import annotations

from collections.abc import Callable

from .exceptions import TaskNotFoundError


class TaskRegistry:
    """Map task names to callables for worker resolution."""

    def __init__(self) -> None:
        self._tasks: dict[str, Callable] = {}

    def register(self, name: str, func: Callable) -> None:
        """Associate a task name with its callable."""
        self._tasks[name] = func

    def get(self, name: str) -> Callable | None:
        """Return a task registered with this queue or registry, if present."""
        return self._tasks.get(name)

    def get_required(self, name: str) -> Callable:
        """Return a registered callable or raise TaskNotFoundError."""
        func = self._tasks.get(name)
        if func is None:
            raise TaskNotFoundError(f"Task '{name}' not found in registry")
        return func

    def remove(self, name: str) -> None:
        """Remove a task by its identifier or registered name."""
        self._tasks.pop(name, None)

    def clear(self) -> None:
        """Remove stored task and result records."""
        self._tasks.clear()

    def list_tasks(self) -> list[str]:
        """Return all registered task names."""
        return list(self._tasks.keys())

    def count(self) -> int:
        """Return the number of registered task callables."""
        return len(self._tasks)

    def __contains__(self, name: str) -> bool:
        return name in self._tasks

    def __iter__(self):
        return iter(self._tasks)


_default_registry = TaskRegistry()


def register_task(name: str, func: Callable) -> None:
    """Register a callable with the default task registry."""
    _default_registry.register(name, func)


def get_task(name: str) -> Callable | None:
    """Return a callable from the default task registry, if present."""
    return _default_registry.get(name)
