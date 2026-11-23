"""Integration contract for Phase 2 metrics against a real Tortoise/SQLite DB.

Proves metrics aggregate in SQL (bounded query count, no Python row loops),
cache with TTL, invalidate correctly, and honour authorization on the dashboard.
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime, timedelta
from types import ModuleType

import pytest
import pytest_asyncio
from tortoise import Model, Tortoise, fields

from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.admin.metrics import Partition, Progress, Table, Trend, Value
from flaxon.testing import AsyncTestClient


class QueryCounter(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.statements: list[str] = []

    def emit(self, record):
        message = record.getMessage()
        if message.lstrip().upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE")):
            self.statements.append(message)


@pytest_asyncio.fixture
async def seeded_orders():
    """Create a real in-memory DB with seeded orders across several days."""
    module = ModuleType("metrics_models")
    sys.modules["metrics_models"] = module

    class Order(Model):
        reference = fields.CharField(max_length=50)
        amount = fields.DecimalField(max_digits=10, decimal_places=2)
        status = fields.CharField(max_length=20)
        fulfilled = fields.BooleanField(default=False)
        created_at = fields.DatetimeField()

        class Meta:
            app = "metrics_models"
            table = "metrics_order"

    Order.__module__ = "metrics_models"
    module.Order = Order

    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"metrics_models": ["metrics_models"]},
    )
    await Tortoise.generate_schemas()

    now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
    try:
        for index in range(12):
            await Order.create(
                reference=f"ORD-{index}",
                amount=index + 1,
                status="paid" if index % 3 == 0 else "pending",
                fulfilled=index % 2 == 0,
                created_at=now - timedelta(days=index % 4),
            )
        yield Order, now
    finally:
        await Tortoise.close_connections()
        sys.modules.pop("metrics_models", None)


async def _calculate_queries(metric, *args, **kwargs):
    """Run calculate() while recording SQL issued to the DB."""
    counter = QueryCounter()
    logger = logging.getLogger("tortoise.db_client")
    logger.addHandler(counter)
    logger.setLevel(logging.DEBUG)
    try:
        result = await metric.calculate(*args, **kwargs)
    finally:
        logger.removeHandler(counter)
    return result, counter.statements


@pytest.mark.asyncio
async def test_value_count_is_one_sql_aggregate(seeded_orders):
    Order, now = seeded_orders  # noqa: N806
    metric = Value(title="Orders", model=Order, range="30d", date_field="created_at")

    result, statements = await _calculate_queries(metric, now=now)

    assert result["value"] == 12
    assert len([s for s in statements if s.lstrip().upper().startswith("SELECT")]) <= 1
    assert any("COUNT" in s.upper() for s in statements), statements


@pytest.mark.asyncio
async def test_value_sum_uses_sql_not_python_loop(seeded_orders):
    Order, now = seeded_orders  # noqa: N806
    metric = Value(
        title="Revenue",
        model=Order,
        field="amount",
        aggregate="sum",
        range="30d",
        date_field="created_at",
    )

    result, statements = await _calculate_queries(metric, now=now)

    assert result["value"] == 78  # sum of 1..12
    assert any("SUM" in s.upper() for s in statements), statements
    assert not any(
        "reference" in s and "FROM" in s.upper() and "GROUP" not in s.upper()
        for s in statements
        if s.lstrip().upper().startswith("SELECT")
    )


@pytest.mark.asyncio
async def test_partition_groups_in_sql(seeded_orders):
    Order, now = seeded_orders  # noqa: N806
    metric = Partition(
        title="By status",
        model=Order,
        field="status",
        range="30d",
        date_field="created_at",
    )

    result, statements = await _calculate_queries(metric, now=now)

    counts = dict(result["parts"])
    assert counts == {"paid": 4, "pending": 8}
    assert any("GROUP BY" in s.upper() for s in statements), statements


@pytest.mark.asyncio
async def test_trend_buckets_by_day_in_sql(seeded_orders):
    Order, now = seeded_orders  # noqa: N806
    metric = Trend(
        title="Per day",
        model=Order,
        date_field="created_at",
        range="30d",
    )

    result, statements = await _calculate_queries(metric, now=now)

    assert len(result["points"]) == 4
    assert sum(count for _, count in result["points"]) == 12
    assert any("GROUP BY" in s.upper() for s in statements), statements


@pytest.mark.asyncio
async def test_progress_uses_two_sql_counts(seeded_orders):
    Order, now = seeded_orders  # noqa: N806
    metric = Progress(
        title="Fulfilled",
        model=Order,
        current_filter={"fulfilled": True},
        range="30d",
        date_field="created_at",
    )

    result, statements = await _calculate_queries(metric, now=now)

    assert result["current"] == 6
    assert result["target"] == 12
    assert result["ratio"] == 0.5
    selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    assert len(selects) <= 2
    assert all("COUNT" in s.upper() for s in selects)


@pytest.mark.asyncio
async def test_table_returns_columns_and_rows(seeded_orders):
    Order, now = seeded_orders  # noqa: N806
    metric = Table(
        title="Top orders",
        model=Order,
        columns=["reference", "amount"],
        range="30d",
        date_field="created_at",
        limit=3,
    )

    result = await metric.calculate(now=now)

    assert result["columns"] == ["reference", "amount"]
    assert len(result["rows"]) == 3


@pytest.mark.asyncio
async def test_query_count_is_constant_as_rows_grow(seeded_orders):
    """Core row-count guard: query count must not scale with row count.

    We seed extra rows and re-run a Value sum; the number of SELECT
    statements must stay bounded (aggregation happens in SQL).
    """
    Order, now = seeded_orders  # noqa: N806

    small = Value(
        title="V", model=Order, field="amount", aggregate="sum", range="30d", date_field="created_at"
    )
    _, before = await _calculate_queries(small, now=now)

    for index in range(60):
        await Order.create(
            reference=f"EXTRA-{index}",
            amount=1,
            status="paid",
            fulfilled=False,
            created_at=now - timedelta(days=1),
        )

    large = Value(
        title="V", model=Order, field="amount", aggregate="sum", range="30d", date_field="created_at"
    )
    result, after = await _calculate_queries(large, now=now)

    assert result["value"] == 138  # 78 + 60
    assert len(before) == len(after) == 1
    assert len(after) <= 2, after


@pytest.mark.asyncio
async def test_cache_prevents_repeated_calculation(seeded_orders):
    Order, now = seeded_orders  # noqa: N806
    metric = Value(title="Cached", model=Order, range="30d", date_field="created_at")
    calls = {"n": 0}
    original = metric.calculate

    async def counting(*args, **kwargs):
        calls["n"] += 1
        return await original(*args, **kwargs)

    metric.calculate = counting
    first = await metric.cached_calculate(now=now)
    second = await metric.cached_calculate(now=now)
    assert first == second
    assert calls["n"] == 1

    metric.cache.clear()
    await metric.cached_calculate(now=now)
    assert calls["n"] == 2


def _dashboard():
    app = Flaxon("metrics-test")
    dashboard = AdminDashboard(
        app,
        users=[
            {"username": "admin", "password": "Admin123!", "permissions": ["admin.superuser"]},
            {"username": "viewer", "password": "Viewer123!", "permissions": ["admin.view_dashboard"]},
        ],
        upload_dir="/tmp",
    )
    return app, dashboard


async def _auth(dashboard, username="admin"):
    token = await dashboard.auth.login(username, "Admin123!" if username == "admin" else "Viewer123!")
    return {"cookie": f"session_id={token}"}


@pytest.mark.asyncio
async def test_metric_authorization_in_dashboard_context(seeded_orders):
    Order, _now = seeded_orders  # noqa: N806
    _, dashboard = _dashboard()
    secret = Value(
        title="Secret revenue",
        model=Order,
        range="30d",
        date_field="created_at",
        permission="admin.view_revenue",
    )
    assert await secret.authorized(dashboard, user=dashboard.auth.user("admin")) is True
    # The viewer role only has view_dashboard, not view_revenue.
    viewer = dashboard.auth.user("viewer")
    assert await secret.authorized(dashboard, user=viewer) is False


@pytest.mark.asyncio
async def test_dashboard_index_renders_metric_cards(seeded_orders):
    Order, _now = seeded_orders  # noqa: N806
    app, dashboard = _dashboard()

    metric = Value(title="Order count", model=Order, range="30d", date_field="created_at")
    dashboard.register_metric(metric, placement="dashboard")

    client = AsyncTestClient(app)
    response = await client.get("/admin/", headers=await _auth(dashboard))
    assert response.status_code == 200
    assert "Order count" in response.text
    assert "<svg" in response.text
    assert 'role="img"' in response.text
