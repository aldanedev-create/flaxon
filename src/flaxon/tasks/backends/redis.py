from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flaxon._imports import import_module
from flaxon.tasks.exceptions import TaskNotFoundError
from flaxon.tasks.result import TaskResult
from flaxon.tasks.task import Task, TaskStatus


class RedisBackend:
    """Store task records and results using an optional Redis client."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "flaxon:task",
        ttl: int = 3600,
    ) -> None:
        self.redis_url = redis_url
        self.prefix = prefix
        self.ttl = ttl
        self._client = None
        self._pub = None
        self._sub = None

    async def connect(self) -> None:
        """Create a Redis client for task storage and queue operations."""
        try:
            redis = import_module("redis.asyncio")

            self._client = redis.from_url(self.redis_url, decode_responses=True)
            self._pub = redis.from_url(self.redis_url, decode_responses=True)
            self._sub = redis.from_url(self.redis_url, decode_responses=True)
        except ImportError as exc:
            raise RuntimeError("redis is required. Install with: pip install redis") from exc

    async def disconnect(self) -> None:
        """Close the Redis client and release the connection."""
        if self._client:
            await self._client.close()
            self._client = None
        if self._pub:
            await self._pub.close()
            self._pub = None
        if self._sub:
            await self._sub.close()
            self._sub = None

    def _task_key(self, task_id: str) -> str:
        return f"{self.prefix}:task:{task_id}"

    def _result_key(self, task_id: str) -> str:
        return f"{self.prefix}:result:{task_id}"

    def _queue_key(self, queue: str) -> str:
        return f"{self.prefix}:queue:{queue}"

    async def store_task(self, task: Task) -> None:
        """Save a task record using its task identifier."""
        data = {
            "id": task.id,
            "name": task.name,
            "status": task.status.value,
            "queue": task.queue,
            "priority": task.priority,
            "retry_count": task.retry_count,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error": task.error,
        }
        await self._client.setex(
            self._task_key(task.id),
            self.ttl,
            json.dumps(data, default=str),
        )

    async def get_task(self, task_id: str) -> Task | None:
        """Read a task record, returning None when it is absent."""
        data = await self._client.get(self._task_key(task_id))
        if data is None:
            return None

        task_data = json.loads(data)
        task = Task(
            name=task_data["name"],
            func=None,
            queue=task_data["queue"],
            priority=task_data["priority"],
        )
        task.id = task_data["id"]
        task.status = TaskStatus(task_data["status"])
        task.retry_count = task_data["retry_count"]
        if task_data.get("created_at"):
            task.created_at = datetime.fromisoformat(task_data["created_at"])
        if task_data.get("started_at"):
            task.started_at = datetime.fromisoformat(task_data["started_at"])
        if task_data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(task_data["completed_at"])
        task.error = task_data.get("error")
        return task

    async def get_task_required(self, task_id: str) -> Task:
        """Read a task record or raise TaskNotFoundError if it is absent."""
        task = await self.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task '{task_id}' not found")
        return task

    async def remove_task(self, task_id: str) -> None:
        """Remove the stored task identified by task_id."""
        await self._client.delete(self._task_key(task_id))

    async def store_result(self, result: TaskResult) -> None:
        """Save the result snapshot for a task."""
        data = result.to_dict()
        data["status"] = data["status"].value if hasattr(data["status"], "value") else data["status"]
        await self._client.setex(
            self._result_key(result.id),
            self.ttl,
            json.dumps(data, default=str),
        )

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Read a stored task result, returning None when it is absent."""
        data = await self._client.get(self._result_key(task_id))
        if data is None:
            return None

        result_data = json.loads(data)
        return TaskResult(
            id=result_data["id"],
            name=result_data["name"],
            status=TaskStatus(result_data["status"]),
            result=result_data.get("result"),
            error=result_data.get("error"),
            retry_count=result_data.get("retry_count", 0),
        )

    async def get_result_required(self, task_id: str) -> TaskResult:
        """Read a stored result or raise TaskNotFoundError if it is absent."""
        result = await self.get_result(task_id)
        if result is None:
            raise TaskNotFoundError(f"Result for task '{task_id}' not found")
        return result

    async def remove_result(self, task_id: str) -> None:
        """Remove the stored result identified by task_id."""
        await self._client.delete(self._result_key(task_id))

    async def push_to_queue(self, queue: str, task_id: str) -> None:
        """Append a task identifier to the named Redis queue."""
        await self._client.lpush(self._queue_key(queue), task_id)

    async def pop_from_queue(self, queue: str, timeout: int = 0) -> str | None:
        """Wait for and remove the next identifier from the named Redis queue."""
        if timeout > 0:
            result = await self._client.brpop(self._queue_key(queue), timeout)
            if result:
                return result[1]
            return None
        return await self._client.rpop(self._queue_key(queue))

    async def clear_queue(self, queue: str) -> None:
        """Remove the named Redis queue."""
        await self._client.delete(self._queue_key(queue))

    async def queue_size(self, queue: str) -> int:
        """Return the number of identifiers in the named Redis queue."""
        return await self._client.llen(self._queue_key(queue))

    async def publish(self, channel: str, message: Any) -> None:
        """Publish a task event on a Redis channel."""
        if not isinstance(message, str):
            message = json.dumps(message, default=str)
        await self._pub.publish(channel, message)

    async def subscribe(self, channel: str) -> Any:
        """Return a Redis subscription for a task event channel."""
        pubsub = self._sub.pubsub()
        await pubsub.subscribe(channel)
        return pubsub
