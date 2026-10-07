"""Cache expiration behavior and boundary cases."""

import pytest

from flaxon.caching.cache import Cache


@pytest.mark.asyncio
async def test_expired_entries_are_missing_to_get_and_exists(monkeypatch):
    monkeypatch.setattr("flaxon.caching.cache.time.time", lambda: 100)
    cache = Cache()
    await cache.set("key", "value", ttl=10)
    monkeypatch.setattr("flaxon.caching.cache.time.time", lambda: 111)
    assert await cache.get("key", "fallback") == "fallback"
    assert not await cache.exists("key")


@pytest.mark.asyncio
async def test_expire_shortens_existing_lifetime(monkeypatch):
    monkeypatch.setattr("flaxon.caching.cache.time.time", lambda: 100)
    cache = Cache()
    await cache.set("key", "value", ttl=100)
    await cache.expire("key", 2)
    monkeypatch.setattr("flaxon.caching.cache.time.time", lambda: 103)
    assert await cache.get("key") is None


@pytest.mark.asyncio
async def test_negative_ttl_keeps_entry_without_expiration(monkeypatch):
    monkeypatch.setattr("flaxon.caching.cache.time.time", lambda: 100)
    cache = Cache()
    await cache.set("key", "value", ttl=-1)
    monkeypatch.setattr("flaxon.caching.cache.time.time", lambda: 100000)
    assert await cache.get("key") == "value"
