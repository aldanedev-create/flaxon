"""Task execution failures behavior and boundary cases."""

import pytest

from flaxon.tasks.retry import RetryPolicy
from flaxon.tasks.task import Task, TaskStatus


@pytest.mark.asyncio
async def test_success_preserves_result_and_completion_snapshot():
    async def double(value):
        return value * 2

    task = Task("double", double)
    assert await task.run(3) == 6
    result = task.to_result()
    assert result.is_completed() and result.is_done() and result.result == 6
    assert result.get_duration() >= 0


@pytest.mark.asyncio
async def test_failed_task_preserves_error_and_final_status():
    async def fail():
        raise ValueError("bad job")

    task = Task("fail", fail, retry_policy=RetryPolicy(max_retries=0))
    with pytest.raises(ValueError, match="bad job"):
        await task.run()
    assert task.status == TaskStatus.FAILED and task.to_result().error == "bad job"


@pytest.mark.asyncio
async def test_retry_succeeds_without_exceeding_limit():
    calls = []

    async def transient():
        calls.append(True)
        if len(calls) < 3:
            raise ConnectionError("temporary")
        return "ready"

    task = Task("transient", transient, retry_policy=RetryPolicy(max_retries=2, delay=0, random_jitter=0))
    assert await task.run() == "ready"
    assert len(calls) == 3 and task.retry_count == 2 and task.status == TaskStatus.COMPLETED
