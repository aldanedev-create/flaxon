from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from datetime import datetime
from typing import Any

from .queue import TaskQueue
from .registry import TaskRegistry
from .task import Task, TaskStatus

logger = logging.getLogger(__name__)


class Worker:
    """Consume queued tasks with bounded retry delays after backend failures."""

    def __init__(
        self,
        registry: TaskRegistry,
        queue: TaskQueue | None = None,
        concurrency: int = 10,
        queue_name: str = "default",
        graceful_shutdown_timeout: int = 30,
    ) -> None:
        self.registry = registry
        self.queue = queue or TaskQueue(name=queue_name)
        self.concurrency = concurrency
        self.queue_name = queue_name
        self.graceful_shutdown_timeout = graceful_shutdown_timeout
        self._running = False
        self._tasks: list[asyncio.Task[Any]] = []
        self._shutdown_event = asyncio.Event()
        self._worker_tasks: list[asyncio.Task[Any]] = []

    async def start(self) -> None:
        """Start consumers and wait for shutdown."""
        self._running = True
        self._shutdown_event.clear()

        for _ in range(self.concurrency):
            worker_task = asyncio.create_task(self._worker_loop())
            self._worker_tasks.append(worker_task)

        loop = asyncio.get_running_loop()
        if hasattr(loop, "add_signal_handler"):
            for sig in (signal.SIGINT, signal.SIGTERM):
                # FIX (SIM105): Replaced try...except with contextlib.suppress
                with contextlib.suppress(NotImplementedError):
                    loop.add_signal_handler(sig, self._handle_shutdown)

        await self._shutdown_event.wait()

    async def _worker_loop(self) -> None:
        retry_delay = 0.1
        while self._running:
            try:
                task = await self.queue.pop(timeout=1.0)
                retry_delay = 0.1
                if task is None:
                    continue

                await self._execute_task(task)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Task worker iteration failed; retrying in %.1fs", retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 5.0)

    async def _execute_task(self, task: Task) -> None:
        try:
            if self.registry.get(task.name) is None:
                task.status = TaskStatus.FAILED
                task.error = f"Task '{task.name}' not found in registry"
                return

            await task.run(*task.args, **task.kwargs)

        except Exception as exc:
            logger.exception("Task execution failed (task_id=%s)", task.id)
            task.error = str(exc)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()

    def _handle_shutdown(self) -> None:
        # Signal callbacks are synchronous: schedule the async drain on the loop.
        self._shutdown_task = asyncio.create_task(self._graceful_shutdown())

    def shutdown(self) -> None:
        """Signal consumers to stop accepting new work (in-flight work is drained)."""
        self._running = False

    async def _graceful_shutdown(self) -> None:
        """Stop accepting new work, then let in-flight tasks finish before cancelling."""
        self._running = False
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._worker_tasks, return_exceptions=True),
                timeout=self.graceful_shutdown_timeout,
            )
        except TimeoutError:
            for task in self._worker_tasks:
                task.cancel()
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)

        self._shutdown_event.set()

    async def stop(self) -> None:
        """Shut down gracefully: drain in-flight tasks, then await consumer cleanup."""
        await self._graceful_shutdown()

    def is_running(self) -> bool:
        """Return whether this worker is accepting tasks."""
        return self._running
