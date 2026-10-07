"""Cache atomic counters behavior and boundary cases."""

import asyncio

import pytest

from flaxon.caching.cache import Cache


@pytest.mark.asyncio
async def test_parallel_increments_are_not_lost():
    cache = Cache()
    results = await asyncio.gather(*(cache.increment("count") for _ in range(100)))
    assert sorted(results) == list(range(1, 101))
    assert await cache.get("count") == 100


@pytest.mark.asyncio
async def test_expired_counter_restarts_from_increment(monkeypatch):
    monkeypatch.setattr("flaxon.caching.cache.time.time", lambda: 100)
    cache = Cache(default_ttl=2)
    await cache.increment("count", 10)
    monkeypatch.setattr("flaxon.caching.cache.time.time", lambda: 103)
    assert await cache.increment("count", 3) == 3


@pytest.mark.asyncio
async def test_decrement_supports_negative_results():
    cache = Cache()
    assert await cache.decrement("count", 2) == -2
    assert await cache.increment("count", 5) == 3
