"""Health registry selection behavior and boundary cases."""

import pytest

from flaxon.health.registry import HealthRegistry
from flaxon.health.response import HealthResponse


@pytest.mark.asyncio
async def test_selected_and_excluded_checks_do_not_run_other_probes():
    called = []
    registry = HealthRegistry()
    registry.register_function("first", lambda: called.append("first") or True)
    registry.register_function("second", lambda: called.append("second") or False)
    results = await registry.run_selected(["first", "unknown"])
    assert [result.name for result in results] == ["first"] and called == ["first"]
    called.clear()
    results = await registry.run_excluding(["first"])
    assert [result.name for result in results] == ["second"] and called == ["second"]


@pytest.mark.asyncio
async def test_unregistered_probe_is_not_run():
    registry = HealthRegistry()
    registry.register_function("service", lambda: True)
    registry.unregister("service")
    assert await registry.run_one("service") is None
    assert await registry.run_all() == []


@pytest.mark.parametrize("status,code", [("healthy", 200), ("degraded", 503), ("unhealthy", 503)])
def test_health_response_status_reflects_availability(status, code):
    response = HealthResponse(status, {"database": "ready"}, version="0.3").to_response()
    assert response.status_code == code
    assert b'"database"' in response.body
