"""Rate limit windows behavior and boundary cases."""

import asyncio

import pytest

from flaxon.security.rate_limit import RateLimiter


@pytest.mark.asyncio
async def test_clients_have_independent_budgets():
    limiter = RateLimiter(requests=2)
    first = {"client": ("192.0.2.1", 1)}
    second = {"client": ("192.0.2.2", 2)}
    assert await limiter.check(first)
    assert await limiter.check(first)
    assert not await limiter.check(first)
    assert await limiter.check(second)
    assert limiter.get_remaining(first) == 0


@pytest.mark.asyncio
async def test_window_expiry_restores_budget(monkeypatch):
    monkeypatch.setattr("flaxon.security.rate_limit.time.monotonic", lambda: 100)
    limiter = RateLimiter(requests=1, window_seconds=10)
    scope = {"client": ("host", 1)}
    assert await limiter.check(scope)
    assert not await limiter.check(scope)
    assert limiter.get_retry_after(scope) > 0
    monkeypatch.setattr("flaxon.security.rate_limit.time.monotonic", lambda: 111)
    assert limiter.get_remaining(scope) == 1
    assert await limiter.check(scope)


@pytest.mark.asyncio
async def test_concurrent_checks_cannot_exceed_budget():
    limiter = RateLimiter(requests=3)
    scope = {"client": ("host", 1)}
    results = await asyncio.gather(*(limiter.check(scope) for _ in range(20)))
    assert sum(results) == 3
