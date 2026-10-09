from __future__ import annotations

import asyncio
import heapq

from .exceptions import TaskQueueError
from .task import Task, TaskStatus


class TaskQueue:
    """An in-process priority queue with task lookup and cancellation helpers."""

    def __init__(self, name: str = "default", max_size: int = 1000) -> None:
        self.name = name
        self.max_size = max_size
        self._queue: list[tuple[int, int, Task]] = []
        self._counter = 0
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition(self._lock)
        self._tasks: dict[str, Task] = {}

    async def push(self, task: Task) -> None:
        """Enqueue a task by priority, raising TaskQueueError when the queue is full."""
        async with self._lock:
            if len(self._queue) >= self.max_size:
                raise TaskQueueError(f"Queue '{self.name}' is full")

            priority = task.priority
            self._counter += 1
            heapq.heappush(self._queue, (priority, self._counter, task))
            self._tasks[task.id] = task
            self._condition.notify()

    async def pop(self, timeout: float | None = None) -> Task | None:
        """Wait for the next queued task, returning None when the timeout expires."""
        async with self._lock:
            while not self._queue:
                if timeout is None:
                    await self._condition.wait()
                else:
                    try:
                        await asyncio.wait_for(self._condition.wait(), timeout)
                    except TimeoutError:
                        return None

            if not self._queue:
                return None

            _, _, task = heapq.heappop(self._queue)
            return task

    async def get(self, task_id: str) -> Task | None:
        """Return a task registered with this queue or registry, if present."""
        async with self._lock:
            return self._tasks.get(task_id)

    async def remove(self, task_id: str) -> bool:
        """Remove a task by its identifier or registered name."""
        async with self._lock:
            task = self._tasks.pop(task_id, None)
            if task is None:
                return False

            for i, (_, _, t) in enumerate(self._queue):
                if t.id == task_id:
                    self._queue.pop(i)
                    heapq.heapify(self._queue)
                    return True

            return True

    async def cancel(self, task_id: str) -> bool:
        """Mark a registered task as cancelled when cancellation is permitted."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False

            task.cancel()
            return True

    async def clear(self) -> None:
        """Remove all waiting entries and registered task records."""
        async with self._lock:
            self._queue.clear()
            self._tasks.clear()

    async def size(self) -> int:
        """Return the number of waiting queue entries."""
        async with self._lock:
            return len(self._queue)

    async def pending_count(self) -> int:
        """Count registered tasks currently marked pending."""
        async with self._lock:
            return len([t for t in self._tasks.values() if t.status == TaskStatus.PENDING])

    async def running_count(self) -> int:
        """Count registered tasks currently marked running."""
        async with self._lock:
            return len([t for t in self._tasks.values() if t.status == TaskStatus.RUNNING])

    async def completed_count(self) -> int:
        """Count registered tasks currently marked completed."""
        async with self._lock:
            return len([t for t in self._tasks.values() if t.status == TaskStatus.COMPLETED])

    async def failed_count(self) -> int:
        """Count registered tasks currently marked failed."""
        async with self._lock:
            return len([t for t in self._tasks.values() if t.status == TaskStatus.FAILED])

    async def get_all_tasks(self) -> list[Task]:
        """Return the task objects registered with this queue."""
        async with self._lock:
            return list(self._tasks.values())

    def __repr__(self) -> str:
        return f"TaskQueue(name={self.name}, size={len(self._queue)})"
