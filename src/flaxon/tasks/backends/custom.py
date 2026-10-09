from __future__ import annotations

from typing import Any

from flaxon.tasks.exceptions import TaskNotFoundError
from flaxon.tasks.result import TaskResult
from flaxon.tasks.task import Task


class CustomBackend:
    """Adapt a supplied backend to the tasks storage interface."""

    def __init__(self, backend: Any) -> None:
        self.backend = backend

    async def start(self) -> None:
        """Start this backend or its background cleanup task."""
        if hasattr(self.backend, "start"):
            result = self.backend.start()
            if hasattr(result, "__await__"):
                await result

    async def stop(self) -> None:
        """Stop the backend and await any background cleanup task."""
        if hasattr(self.backend, "stop"):
            result = self.backend.stop()
            if hasattr(result, "__await__"):
                await result

    async def store_task(self, task: Task) -> None:
        """Save a task record using its task identifier."""
        if hasattr(self.backend, "store_task"):
            result = self.backend.store_task(task)
            if hasattr(result, "__await__"):
                await result
        elif hasattr(self.backend, "save_task"):
            result = self.backend.save_task(task)
            if hasattr(result, "__await__"):
                await result
        else:
            raise NotImplementedError("Backend does not support store_task")

    async def get_task(self, task_id: str) -> Task | None:
        """Read a task record, returning None when it is absent."""
        if hasattr(self.backend, "get_task"):
            result = self.backend.get_task(task_id)
            if hasattr(result, "__await__"):
                return await result
            return result
        if hasattr(self.backend, "load_task"):
            result = self.backend.load_task(task_id)
            if hasattr(result, "__await__"):
                return await result
            return result
        raise NotImplementedError("Backend does not support get_task")

    async def get_task_required(self, task_id: str) -> Task:
        """Read a task record or raise TaskNotFoundError if it is absent."""
        task = await self.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task '{task_id}' not found")
        return task

    async def remove_task(self, task_id: str) -> None:
        """Remove the stored task identified by task_id."""
        if hasattr(self.backend, "remove_task"):
            result = self.backend.remove_task(task_id)
            if hasattr(result, "__await__"):
                await result
        elif hasattr(self.backend, "delete_task"):
            result = self.backend.delete_task(task_id)
            if hasattr(result, "__await__"):
                await result
        else:
            raise NotImplementedError("Backend does not support remove_task")

    async def store_result(self, result: TaskResult) -> None:
        """Save the result snapshot for a task."""
        if hasattr(self.backend, "store_result"):
            result_obj = self.backend.store_result(result)
            if hasattr(result_obj, "__await__"):
                await result_obj
        elif hasattr(self.backend, "save_result"):
            result_obj = self.backend.save_result(result)
            if hasattr(result_obj, "__await__"):
                await result_obj
        else:
            raise NotImplementedError("Backend does not support store_result")

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Read a stored task result, returning None when it is absent."""
        if hasattr(self.backend, "get_result"):
            result = self.backend.get_result(task_id)
            if hasattr(result, "__await__"):
                return await result
            return result
        if hasattr(self.backend, "load_result"):
            result = self.backend.load_result(task_id)
            if hasattr(result, "__await__"):
                return await result
            return result
        raise NotImplementedError("Backend does not support get_result")

    async def get_result_required(self, task_id: str) -> TaskResult:
        """Read a stored result or raise TaskNotFoundError if it is absent."""
        result = await self.get_result(task_id)
        if result is None:
            raise TaskNotFoundError(f"Result for task '{task_id}' not found")
        return result

    async def remove_result(self, task_id: str) -> None:
        """Remove the stored result identified by task_id."""
        if hasattr(self.backend, "remove_result"):
            result = self.backend.remove_result(task_id)
            if hasattr(result, "__await__"):
                await result
        elif hasattr(self.backend, "delete_result"):
            result = self.backend.delete_result(task_id)
            if hasattr(result, "__await__"):
                await result
        else:
            raise NotImplementedError("Backend does not support remove_result")

    async def clear(self) -> None:
        """Remove stored task and result records."""
        if hasattr(self.backend, "clear"):
            result = self.backend.clear()
            if hasattr(result, "__await__"):
                await result
