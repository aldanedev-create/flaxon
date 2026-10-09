from __future__ import annotations

from flaxon.exceptions import FlaxonError


class TaskError(FlaxonError):
    """Base exception for background task failures."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class TaskNotFoundError(TaskError):
    """A required task or task result could not be found."""

    def __init__(self, message: str = "Task not found") -> None:
        super().__init__(message)


class TaskQueueError(TaskError):
    """A task queue operation failed."""

    def __init__(self, message: str = "Task queue error") -> None:
        super().__init__(message)


class TaskResultError(TaskError):
    """A task result operation failed."""

    def __init__(self, message: str = "Task result error") -> None:
        super().__init__(message)


class TaskTimeoutError(TaskError):
    """A task exceeded its execution timeout."""

    def __init__(self, message: str = "Task timed out") -> None:
        super().__init__(message)


class TaskRegistrationError(TaskError):
    """A task could not be registered."""

    def __init__(self, message: str = "Task registration error") -> None:
        super().__init__(message)


class TaskExecutionError(TaskError):
    """A task callable could not be executed successfully."""

    def __init__(self, message: str = "Task execution error") -> None:
        super().__init__(message)
