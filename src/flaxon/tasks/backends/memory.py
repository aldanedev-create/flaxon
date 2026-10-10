from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime

from flaxon.tasks.exceptions import TaskNotFoundError
from flaxon.tasks.result import TaskResult
from flaxon.tasks.task import Task, TaskStatus


class MemoryBackend:
    """Store task records and results in this process with background expiration cleanup."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._results: dict[str, TaskResult] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start this backend or its background cleanup task."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop the backend and await any background cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

    async def store_task(self, task: Task) -> None:
        """Save a task record using its task identifier."""
        async with self._lock:
            self._tasks[task.id] = task

    async def get_task(self, task_id: str) -> Task | None:
        """Read a task record, returning None when it is absent."""
        async with self._lock:
            return self._tasks.get(task_id)

    async def get_task_required(self, task_id: str) -> Task:
        """Read a task record or raise TaskNotFoundError if it is absent."""
        task = await self.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task '{task_id}' not found")
        return task

    async def remove_task(self, task_id: str) -> None:
        """Remove the stored task identified by task_id."""
        async with self._lock:
            self._tasks.pop(task_id, None)

    async def store_result(self, result: TaskResult) -> None:
        """Save the result snapshot for a task."""
        async with self._lock:
            self._results[result.id] = result

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Read a stored task result, returning None when it is absent."""
        async with self._lock:
            return self._results.get(task_id)

    async def get_result_required(self, task_id: str) -> TaskResult:
        """Read a stored result or raise TaskNotFoundError if it is absent."""
        result = await self.get_result(task_id)
        if result is None:
            raise TaskNotFoundError(f"Result for task '{task_id}' not found")
        return result

    async def remove_result(self, task_id: str) -> None:
        """Remove the stored result identified by task_id."""
        async with self._lock:
            self._results.pop(task_id, None)

    async def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """Return stored tasks using the available queue and status filters."""
        async with self._lock:
            if status is None:
                return list(self._tasks.values())
            return [t for t in self._tasks.values() if t.status == status]

    async def list_results(self, status: TaskStatus | None = None) -> list[TaskResult]:
        """Return stored task result snapshots."""
        async with self._lock:
            if status is None:
                return list(self._results.values())
            return [r for r in self._results.values() if r.status == status]

    async def clear(self) -> None:
        """Remove stored task and result records."""
        async with self._lock:
            self._tasks.clear()
            self._results.clear()

    async def _cleanup_loop(self) -> None:
        while self._running:
            await asyncio.sleep(60)

            async with self._lock:
                now = datetime.now()
                to_remove = []

                for task_id, task in self._tasks.items():
                    if task.completed_at:
                        age = (now - task.completed_at).total_seconds()
                        if age > 3600:
                            to_remove.append(task_id)

                for task_id in to_remove:
                    self._tasks.pop(task_id, None)
                    self._results.pop(task_id, None)
