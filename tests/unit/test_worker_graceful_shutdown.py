"""Worker shutdown must drain in-flight tasks instead of cancelling them outright."""

from __future__ import annotations

import asyncio

import pytest

from flaxon.tasks.queue import TaskQueue
from flaxon.tasks.registry import TaskRegistry
from flaxon.tasks.task import Task
from flaxon.tasks.worker import Worker


@pytest.mark.asyncio
async def test_stop_drains_in_flight_task_before_returning():
    registry = TaskRegistry()
    queue = TaskQueue()
    finished = []

    async def slow_job():
        await asyncio.sleep(0.2)
        finished.append("done")

    registry.register("slow_job", slow_job)
    await queue.push(Task(name="slow_job", func=slow_job))

    worker = Worker(registry, queue, concurrency=1, graceful_shutdown_timeout=5)
    loop_task = asyncio.create_task(worker.start())
    await asyncio.sleep(0.05)  # let the worker pick up the job

    await worker.stop()
    await loop_task
    assert finished == ["done"], "in-flight task was cancelled by shutdown"


@pytest.mark.asyncio
async def test_shutdown_stops_accepting_new_work():
    registry = TaskRegistry()
    worker = Worker(registry, TaskQueue(), concurrency=1)
    worker.shutdown()
    assert worker.is_running() is False
