"""Cache batch operations behavior and boundary cases."""

import pytest

from flaxon.caching.cache import Cache


@pytest.mark.asyncio
async def test_many_operations_preserve_falsey_values_and_ignore_missing():
    cache = Cache()
    await cache.set_many({"zero": 0, "false": False, "empty": ""})
    assert await cache.get_many("zero", "false", "empty", "missing") == {
        "zero": 0,
        "false": False,
        "empty": "",
    }
    await cache.delete_many("false", "missing")
    assert await cache.get_many("zero", "false") == {"zero": 0}


@pytest.mark.asyncio
async def test_clear_does_not_affect_other_cache_instance():
    first = Cache()
    second = Cache()
    await first.set("a", 1)
    await second.set("a", 2)
    await first.clear()
    assert await first.get("a") is None
    assert await second.get("a") == 2


@pytest.mark.asyncio
async def test_delete_is_idempotent():
    cache = Cache()
    await cache.set("a", 1)
    await cache.delete("a")
    await cache.delete("a")
    assert not await cache.exists("a")
