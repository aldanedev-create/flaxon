"""Async handlers must not do blocking file I/O or run sync callables on the loop."""

from __future__ import annotations

import threading

import pytest

from flaxon.exceptions import NotFound
from flaxon.static import StaticFiles
from flaxon.tasks import Task


@pytest.mark.asyncio
async def test_static_file_read_does_not_block_the_event_loop(tmp_path):
    payload = tmp_path / "asset.txt"
    payload.write_bytes(b"hello")
    # Verify the file read happens off the event-loop thread.
    loop_thread = threading.current_thread()

    original = type(payload).read_bytes

    def tracked_read(self):
        assert threading.current_thread() is not loop_thread, (
            "StaticFiles.read_bytes ran on the event-loop thread"
        )
        return original(self)

    payload.__class__.read_bytes = tracked_read  # type: ignore[method-assign]
    try:
        handler = StaticFiles(str(tmp_path))
        response = await handler(object(), "asset.txt")  # type: ignore[arg-type]
        assert response.body == b"hello"
    finally:
        payload.__class__.read_bytes = original  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_sync_task_runs_off_the_event_loop_thread():
    loop_thread = threading.current_thread()
    ran_on: list[threading.Thread] = []

    def sync_work():
        ran_on.append(threading.current_thread())
        return "done"

    task = Task(name="sync", func=sync_work)
    result = await task.run()
    assert result == "done"
    assert ran_on and ran_on[0] is not loop_thread, "sync task callable ran on the event-loop thread"


@pytest.mark.asyncio
async def test_static_missing_file_still_raises_not_found(tmp_path):
    handler = StaticFiles(str(tmp_path))
    with pytest.raises(NotFound):
        await handler(object(), "missing.txt")  # type: ignore[arg-type]
