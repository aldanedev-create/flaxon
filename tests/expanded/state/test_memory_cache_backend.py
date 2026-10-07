"""Memory cache backend behavior and boundary cases."""

import pytest

from flaxon.caching.backends.memory import MemoryBackend


@pytest.mark.asyncio
async def test_bulk_backend_operations_keep_values():
    backend = MemoryBackend()
    await backend.set_many({"a": 1, "b": False})
    assert await backend.get_many(["a", "b", "missing"]) == {"a": 1, "b": False}
    await backend.delete_many(["a", "missing"])
    assert await backend.get("a") is None
    assert await backend.get("b") is False


@pytest.mark.asyncio
async def test_backend_expiration_and_stats(monkeypatch):
    monkeypatch.setattr("flaxon.caching.backends.memory.time.time", lambda: 100)
    backend = MemoryBackend()
    await backend.set("short", 1, ttl=2)
    await backend.set("forever", 2)
    monkeypatch.setattr("flaxon.caching.backends.memory.time.time", lambda: 103)
    assert backend.get_stats() == {"total_entries": 2, "expired_entries": 1, "active_entries": 1}
    assert not await backend.exists("short")
    assert await backend.get("forever") == 2


@pytest.mark.asyncio
async def test_cleanup_task_can_be_stopped_without_leaking():
    backend = MemoryBackend()
    await backend.start()
    task = backend._cleanup_task
    await backend.stop()
    assert task.done()
    assert backend._cleanup_task is None
