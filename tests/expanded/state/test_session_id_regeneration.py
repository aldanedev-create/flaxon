"""Session id regeneration behavior and boundary cases."""

import pytest

from flaxon.sessions.backends.memory import MemoryBackend
from flaxon.sessions.manager import SessionManager


@pytest.mark.asyncio
async def test_regeneration_invalidates_old_id_and_keeps_data():
    manager = SessionManager(MemoryBackend(), "secret")
    session = await manager.create({"user": "alice"})
    old_id = session.id
    regenerated = await manager.regenerate(session)
    assert regenerated.id != old_id
    assert await manager.get(old_id) is None
    assert (await manager.get(regenerated.id))["user"] == "alice"


@pytest.mark.asyncio
async def test_missing_id_creates_new_session():
    manager = SessionManager(MemoryBackend(), "secret")
    first = await manager.get_or_create("not-found")
    second = await manager.get_or_create(first.id)
    assert first.id == second.id


@pytest.mark.asyncio
async def test_expired_session_is_not_reused(monkeypatch):
    monkeypatch.setattr("flaxon.sessions.backends.memory.time.time", lambda: 100)
    manager = SessionManager(MemoryBackend(), "secret", ttl=2)
    session = await manager.create()
    monkeypatch.setattr("flaxon.sessions.backends.memory.time.time", lambda: 103)
    assert (await manager.get_or_create(session.id)).id != session.id
