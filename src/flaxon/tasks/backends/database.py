from __future__ import annotations

import json
from typing import Any

from flaxon.tasks.exceptions import TaskNotFoundError
from flaxon.tasks.result import TaskResult
from flaxon.tasks.task import Task, TaskStatus


class DatabaseBackend:
    """Store task records and results through a database manager."""

    def __init__(
        self,
        db_manager: Any,
        table_name: str = "tasks",
        result_table: str = "task_results",
    ) -> None:
        self.db = db_manager
        self.table_name = table_name
        self.result_table = result_table

    async def initialize(self) -> None:
        """Create the task and result tables if they do not exist."""
        await self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id VARCHAR(64) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(32) NOT NULL,
                queue VARCHAR(64) NOT NULL,
                priority INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error TEXT
            )
        """)

        await self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.result_table} (
                task_id VARCHAR(64) PRIMARY KEY,
                result TEXT,
                status VARCHAR(32) NOT NULL,
                created_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                retry_count INTEGER DEFAULT 0
            )
        """)

    async def store_task(self, task: Task) -> None:
        """Save a task record using its task identifier."""
        await self.db.execute(
            f"""
            INSERT OR REPLACE INTO {self.table_name}
            (id, name, status, queue, priority, retry_count, created_at, started_at, completed_at, error)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            task.id,
            task.name,
            task.status.value,
            task.queue,
            task.priority,
            task.retry_count,
            task.created_at,
            task.started_at,
            task.completed_at,
            task.error,
        )

    async def get_task(self, task_id: str) -> Task | None:
        """Read a task record, returning None when it is absent."""
        row = await self.db.fetch_one(
            f"SELECT * FROM {self.table_name} WHERE id = $1",
            task_id,
        )
        if row is None:
            return None

        task = Task(
            name=row["name"],
            func=None,
            queue=row["queue"],
            priority=row["priority"],
        )
        task.id = row["id"]
        task.status = TaskStatus(row["status"])
        task.retry_count = row["retry_count"]
        task.created_at = row["created_at"]
        task.started_at = row["started_at"]
        task.completed_at = row["completed_at"]
        task.error = row["error"]
        return task

    async def get_task_required(self, task_id: str) -> Task:
        """Read a task record or raise TaskNotFoundError if it is absent."""
        task = await self.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task '{task_id}' not found")
        return task

    async def remove_task(self, task_id: str) -> None:
        """Remove the stored task identified by task_id."""
        await self.db.execute(
            f"DELETE FROM {self.table_name} WHERE id = $1",
            task_id,
        )

    async def store_result(self, result: TaskResult) -> None:
        """Save the result snapshot for a task."""
        await self.db.execute(
            f"""
            INSERT OR REPLACE INTO {self.result_table}
            (task_id, result, status, created_at, completed_at, retry_count)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            result.id,
            json.dumps(result.result, default=str) if result.result is not None else None,
            result.status.value,
            result.created_at,
            result.completed_at,
            result.retry_count,
        )

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Read a stored task result, returning None when it is absent."""
        row = await self.db.fetch_one(
            f"SELECT * FROM {self.result_table} WHERE task_id = $1",
            task_id,
        )
        if row is None:
            return None

        return TaskResult(
            id=row["task_id"],
            name="",
            status=TaskStatus(row["status"]),
            result=json.loads(row["result"]) if row["result"] else None,
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            retry_count=row["retry_count"],
        )

    async def get_result_required(self, task_id: str) -> TaskResult:
        """Read a stored result or raise TaskNotFoundError if it is absent."""
        result = await self.get_result(task_id)
        if result is None:
            raise TaskNotFoundError(f"Result for task '{task_id}' not found")
        return result

    async def remove_result(self, task_id: str) -> None:
        """Remove the stored result identified by task_id."""
        await self.db.execute(
            f"DELETE FROM {self.result_table} WHERE task_id = $1",
            task_id,
        )

    async def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """Return stored tasks using the available queue and status filters."""
        if status is None:
            rows = await self.db.fetch_all(f"SELECT * FROM {self.table_name}")
        else:
            rows = await self.db.fetch_all(
                f"SELECT * FROM {self.table_name} WHERE status = $1",
                status.value,
            )

        tasks = []
        for row in rows:
            task = Task(
                name=row["name"],
                func=None,
                queue=row["queue"],
                priority=row["priority"],
            )
            task.id = row["id"]
            task.status = TaskStatus(row["status"])
            task.retry_count = row["retry_count"]
            task.created_at = row["created_at"]
            task.started_at = row["started_at"]
            task.completed_at = row["completed_at"]
            task.error = row["error"]
            tasks.append(task)

        return tasks

    async def clear(self) -> None:
        """Remove stored task and result records."""
        await self.db.execute(f"DELETE FROM {self.table_name}")
        await self.db.execute(f"DELETE FROM {self.result_table}")
