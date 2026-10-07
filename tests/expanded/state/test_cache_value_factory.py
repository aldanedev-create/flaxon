"""Cache value factory behavior and boundary cases."""

import pytest

from flaxon.caching.cache import Cache


@pytest.mark.asyncio
async def test_async_factory_runs_only_for_missing_value():
    calls = []

    async def factory():
        calls.append(1)
        return {"id": 1}

    cache = Cache()
    assert await cache.get_or_set("a", factory) == {"id": 1}
    assert await cache.get_or_set("a", factory) == {"id": 1}
    assert calls == [1]


@pytest.mark.asyncio
async def test_sync_factory_supports_falsey_result():
    calls = []

    def factory():
        calls.append(1)
        return False

    cache = Cache()
    assert await cache.get_or_set("a", factory) is False
    assert await cache.get_or_set("a", factory) is False
    assert calls == [1]


@pytest.mark.asyncio
async def test_failed_factory_does_not_cache_partial_result():
    def factory():
        raise ValueError("failure")

    cache = Cache()
    with pytest.raises(ValueError):
        await cache.get_or_set("a", factory)
    assert not await cache.exists("a")
