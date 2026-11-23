"""The distributed limiter must request an atomic Redis pipeline explicitly.

A bare ``pipeline()`` relies on the client default; a redis-py client configured with
``pipeline(transaction=False)`` (or a non-transactional compatible client) would allow a
thundering herd to all observe the same ZCARD and blow past the limit. The fix requests a
MULTI/EXEC transaction explicitly and this test would fail without it.
"""

from __future__ import annotations

import asyncio

import pytest

from flaxon.security.rate_limit import DistributedRateLimiter


class _AtomicPipeline:
    """A minimal pipeline that is atomic only when transaction=True was requested."""

    def __init__(self, store: dict, transaction: bool):
        self.store = store
        self.transaction = transaction
        self.commands: list = []

    def zremrangebyscore(self, key, start, end):
        self.commands.append(("zremrangebyscore", key, start, end))
        return self

    def zcard(self, key):
        self.commands.append(("zcard", key))
        return self

    def zadd(self, key, mapping):
        self.commands.append(("zadd", key, mapping))
        return self

    def expire(self, key, seconds):
        self.commands.append(("expire", key, seconds))
        return self

    async def execute(self):
        if not self.transaction:
            raise AssertionError("pipeline() was called without transaction=True")
        # Serialize the whole batch as one MULTI/EXEC-style block, returning
        # one result per queued command (zrem/zcard/zadd/expire).
        results = [0] * len(self.commands)
        self.commands.clear()
        return results


class _TrackingRedis:
    def __init__(self, transaction_seen: list[bool | None]):
        self.transaction_seen = transaction_seen

    def pipeline(self, transaction=None):
        self.transaction_seen.append(transaction)
        return _AtomicPipeline({}, transaction=bool(transaction))


@pytest.mark.asyncio
async def test_distributed_limiter_requires_atomic_pipeline():
    seen: list[bool | None] = []
    limiter = DistributedRateLimiter(_TrackingRedis(seen), prefix="atomic")
    allowed = await limiter.check("user:1", requests=10, window_seconds=60)
    assert allowed is True
    assert seen == [True], "check() must request pipeline(transaction=True) for atomicity"


@pytest.mark.asyncio
async def test_concurrent_checks_do_not_exceed_limit_with_serialized_pipeline():
    """Simulate a MULTI/EXEC pipeline where each check increments a shared counter."""
    counter = {"value": 0}
    seen: list[bool | None] = []

    class SerialRedis:
        def pipeline(self, transaction=None):
            seen.append(transaction)
            assert transaction is True
            p = _AtomicPipeline({}, transaction=True)

            # Override execute to model ZCARD seeing all prior committed transactions.
            async def execute():
                current = counter["value"]
                counter["value"] += 1
                return [None, current, None, None]

            p.execute = execute  # type: ignore[method-assign]
            return p

    limiter = DistributedRateLimiter(SerialRedis(), prefix="atomic")
    results = await asyncio.gather(
        *(limiter.check("burst", requests=25, window_seconds=60) for _ in range(100))
    )
    assert sum(results) == 25
