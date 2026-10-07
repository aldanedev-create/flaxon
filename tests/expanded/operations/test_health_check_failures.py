"""Health check failures behavior and boundary cases."""

import asyncio

import pytest

from flaxon.health.checks import HealthCheck


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value,status",
    [(True, "healthy"), (False, "unhealthy"), ({"status": "degraded", "message": "slow"}, "degraded")],
)
async def test_results_are_normalized(value, status):
    result = await HealthCheck("service", lambda: value).run()
    assert result.name == "service" and result.status == status
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_exception_becomes_unhealthy_result():
    def fail():
        raise ConnectionError("offline")

    result = await HealthCheck("service", fail).run()
    assert result.is_unhealthy() and result.message == "offline"


@pytest.mark.asyncio
async def test_timeout_cancels_probe_and_reports_failure():
    cancelled = []

    async def blocked():
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    result = await HealthCheck("service", blocked, timeout=0.01).run()
    assert result.is_unhealthy() and "timed out" in result.message
    assert cancelled == [True]
