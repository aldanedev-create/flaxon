from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Any

# FIX (UP042): Use StrEnum instead of subclassing (str, Enum)
from flaxon._imports import import_attribute

from .context import TaskContext
from .exceptions import TaskError
from .retry import RetryPolicy


class TaskStatus(StrEnum):
    """The lifecycle states recorded by a background task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class Task:
    """Execute a callable while recording status, retries, results, and errors."""

    def __init__(
        self,
        name: str,
        func: Callable,
        *,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        retry_policy: RetryPolicy | None = None,
        timeout: int | None = None,
        queue: str = "default",
        priority: int = 0,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = dict(kwargs or {})
        self.retry_policy = retry_policy or RetryPolicy()
        self.timeout = timeout
        self.queue = queue
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.result: Any = None
        self.error: str | None = None
        self.retry_count = 0
        self._context: TaskContext | None = None

    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the task callable and record its outcome, applying retries if allowed."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        self._context = TaskContext(self.id, self.name)

        try:
            if asyncio.iscoroutinefunction(self.func):
                if self.timeout:
                    result = await asyncio.wait_for(
                        self.func(*args, **kwargs),
                        timeout=self.timeout,
                    )
                else:
                    result = await self.func(*args, **kwargs)
            elif self.timeout:
                # FIX (E501): Split long line across multiple lines
                result = await asyncio.wait_for(
                    asyncio.to_thread(self.func, *args, **kwargs),
                    timeout=self.timeout,
                )
            else:
                result = self.func(*args, **kwargs)

            self.status = TaskStatus.COMPLETED
            self.completed_at = datetime.now()
            self.result = result
            return result

        except TimeoutError:
            self.status = TaskStatus.TIMEOUT
            self.error = f"Task timed out after {self.timeout} seconds"
            # FIX (B904): Use 'raise ... from None' to prevent exception chaining confusion
            raise TaskError(self.error) from None

        except Exception as exc:
            self.error = str(exc)
            if self.retry_policy and self.retry_policy.should_retry(self.retry_count, exc):
                self.status = TaskStatus.RETRY
                self.retry_count += 1
                await asyncio.sleep(self.retry_policy.get_delay(self.retry_count))
                return await self.run(*args, **kwargs)

            self.status = TaskStatus.FAILED
            self.completed_at = datetime.now()
            raise

    def cancel(self) -> None:
        """Mark a registered task as cancelled when cancellation is permitted."""
        if self.status in {TaskStatus.PENDING, TaskStatus.RUNNING}:
            self.status = TaskStatus.CANCELLED
            self.completed_at = datetime.now()

    def to_result(self) -> Any:
        """Return a serializable snapshot of this task's final state."""
        # FIX (PLC0415): Moved import to top-level if possible, or kept local if required to avoid circular
        # dependency
        task_result_type = import_attribute("flaxon.tasks.result", "TaskResult")

        return task_result_type(
            id=self.id,
            name=self.name,
            status=self.status,
            result=self.result,
            error=self.error,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            retry_count=self.retry_count,
        )

    def __repr__(self) -> str:
        return f"Task(id={self.id}, name={self.name}, status={self.status.value})"


def task(
    name: str | None = None,
    *,
    retry_policy: RetryPolicy | None = None,
    timeout: int | None = None,
    queue: str = "default",
    priority: int = 0,
) -> Callable:
    """Decorate a callable to construct a configured Task object."""

    def decorator(func: Callable) -> Task:
        task_name = name or func.__name__
        return Task(
            name=task_name,
            func=func,
            retry_policy=retry_policy,
            timeout=timeout,
            queue=queue,
            priority=priority,
        )

    return decorator
