from __future__ import annotations

import asyncio

# FIX: Import contextlib to replace try/except with contextlib.suppress (SIM105)
import contextlib
import datetime
from collections.abc import Callable
from typing import Any

from .exceptions import TaskError
from .queue import TaskQueue
from .task import Task


class Scheduler:

    def __init__(self, queue: TaskQueue) -> None:
        self.queue = queue
        self._scheduled_tasks: list[dict[str, Any]] = []
        self._running = False
        self._scheduler_task: asyncio.Task | None = None

    def schedule(
        self,
        task: Task,
        delay: int | None = None,
        at: datetime.datetime | None = None,
        interval: int | None = None,
    ) -> None:
        schedule_time = (
            datetime.datetime.now() + datetime.timedelta(seconds=delay)
            if delay
            else at
        )

        if schedule_time is None:
            schedule_time = datetime.datetime.now()

        self._scheduled_tasks.append(
            {
                "task": task,
                "schedule_time": schedule_time,
                "interval": interval,
                "next_run": schedule_time,
            }
        )

    async def start(self) -> None:
        self._running = True
        self._scheduler_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            # FIX (SIM105): Use contextlib.suppress instead of try...except pass
            with contextlib.suppress(asyncio.CancelledError):
                await self._scheduler_task
            self._scheduler_task = None

    async def _run(self) -> None:
        while self._running:
            await self.run_once()
            await asyncio.sleep(1)

    async def run_once(self) -> None:
        """Run a single scheduling pass: push any due tasks onto the queue."""
        now = datetime.datetime.now()
        to_run = []

        for item in self._scheduled_tasks[:]:
            if item["next_run"] <= now:
                to_run.append(item)
                if item["interval"]:
                    item["next_run"] += datetime.timedelta(
                        seconds=item["interval"]
                    )
                else:
                    self._scheduled_tasks.remove(item)

        for item in to_run:
            # FIX (SIM105): Use contextlib.suppress instead of try...except pass
            with contextlib.suppress(TaskError):
                await self.queue.push(item["task"])


def scheduled_task(
    interval: int | None = None,
    delay: int | None = None,
    at: datetime.datetime | None = None,
    queue: str = "default",
) -> Callable:
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator
