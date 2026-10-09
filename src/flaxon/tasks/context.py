from __future__ import annotations

import contextvars
from typing import Any


class TaskContext:
    """Expose task identity and copy-on-write task-local values."""

    _current_task_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "current_task_id", default=None
    )
    _current_task_name: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "current_task_name", default=None
    )
    _task_data: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
        "task_data", default=None
    )

    def __init__(self, task_id: str | None = None, task_name: str | None = None) -> None:
        self._task_id = task_id
        self._task_name = task_name

    def __enter__(self) -> TaskContext:
        if self._task_id is not None:
            self._token_id = TaskContext._current_task_id.set(self._task_id)
        if self._task_name is not None:
            self._token_name = TaskContext._current_task_name.set(self._task_name)
        self._token_data = TaskContext._task_data.set({})
        return self

    def __exit__(self, *args: Any) -> None:
        if hasattr(self, "_token_id"):
            TaskContext._current_task_id.reset(self._token_id)
        if hasattr(self, "_token_name"):
            TaskContext._current_task_name.reset(self._token_name)
        if hasattr(self, "_token_data"):
            TaskContext._task_data.reset(self._token_data)

    @classmethod
    def get_current_task_id(cls) -> str | None:
        """Return the task identifier in the active context, if any."""
        return cls._current_task_id.get()

    @classmethod
    def get_current_task_name(cls) -> str | None:
        """Return the task name in the active context, if any."""
        return cls._current_task_name.get()

    @classmethod
    def get_data(cls, key: str, default: Any = None) -> Any:
        """Read a task-local value or return the supplied fallback."""
        return (cls._task_data.get() or {}).get(key, default)

    @classmethod
    def set_data(cls, key: str, value: Any) -> None:
        """Set a task-local value without mutating inherited context data."""
        data = dict(cls._task_data.get() or {})
        data[key] = value
        cls._task_data.set(data)

    @classmethod
    def get_all_data(cls) -> dict[str, Any]:
        """Return a shallow copy of the active task data."""
        return dict(cls._task_data.get() or {})


def get_current_task_id() -> str | None:
    """Return the task identifier in the active context, if any."""
    return TaskContext.get_current_task_id()


def get_current_task_name() -> str | None:
    """Return the task name in the active context, if any."""
    return TaskContext.get_current_task_name()


def get_task_data(key: str, default: Any = None) -> Any:
    """Read a value from the active task context."""
    return TaskContext.get_data(key, default)


def set_task_data(key: str, value: Any) -> None:
    """Write a value to the active task context."""
    TaskContext.set_data(key, value)


def get_all_task_data() -> dict[str, Any]:
    """Return a shallow copy of the active task context data."""
    return TaskContext.get_all_data()
