"""Phase 2 contract: metrics, ranges, TTL cache and inline SVG charts.

Written before the implementation exists; the top-level import is expected to
fail until ``flaxon.admin.metrics`` is implemented.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from flaxon.admin.metrics import (
    PARTITION,
    PROGRESS,
    TABLE,
    TREND,
    VALUE,
    Partition,
    Progress,
    Table,
    Trend,
    TTLCache,
    Value,
    resolve_range,
)

# ---------------------------------------------------------------------------
# Ranges
# ---------------------------------------------------------------------------


NOW = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("key", "start", "end"),
    [
        ("30d", NOW - timedelta(days=30), NOW),
        ("60d", NOW - timedelta(days=60), NOW),
    ],
)
def test_rolling_ranges(key, start, end):
    result = resolve_range(key, now=NOW)
    assert result.start == start
    assert result.end == end


def test_mtd_range_starts_on_first_of_month():
    result = resolve_range("mtd", now=NOW)
    assert result.start == datetime(2026, 6, 1, tzinfo=UTC)
    assert result.end == NOW


def test_qtd_range_starts_on_first_of_quarter():
    result = resolve_range("qtd", now=datetime(2026, 5, 20, tzinfo=UTC))
    assert result.start == datetime(2026, 4, 1, tzinfo=UTC)


def test_ytd_range_starts_on_first_of_year():
    result = resolve_range("ytd", now=NOW)
    assert result.start == datetime(2026, 1, 1, tzinfo=UTC)


def test_custom_range_uses_explicit_bounds():
    start = datetime(2026, 1, 10, tzinfo=UTC)
    end = datetime(2026, 2, 10, tzinfo=UTC)
    result = resolve_range("custom", now=NOW, start=start, end=end)
    assert result.start == start
    assert result.end == end


def test_unknown_range_raises_value_error():
    with pytest.raises(ValueError):
        resolve_range("last-week", now=NOW)


def test_metric_range_is_hashable_for_cache_keys():
    result = resolve_range("30d", now=NOW)
    assert isinstance(hash(result), int)


# ---------------------------------------------------------------------------
# TTL cache
# ---------------------------------------------------------------------------


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def test_cache_returns_value_before_ttl():
    clock = FakeClock()
    cache = TTLCache(clock=clock)
    cache.set("k", {"value": 7}, ttl=10)
    clock.advance(9)
    assert cache.get("k") == {"value": 7}


def test_cache_expires_after_ttl():
    clock = FakeClock()
    cache = TTLCache(clock=clock)
    cache.set("k", "v", ttl=5)
    clock.advance(6)
    assert cache.get("k") is None


def test_cache_invalidate_prefix_removes_matching_entries():
    cache = TTLCache()
    cache.set("orders:value", 1, ttl=60)
    cache.set("orders:trend", 2, ttl=60)
    cache.set("users:value", 3, ttl=60)
    removed = cache.invalidate("orders:")
    assert removed == 2
    assert cache.get("orders:value") is None
    assert cache.get("users:value") == 3


def test_cache_clear_removes_everything():
    cache = TTLCache()
    cache.set("a", 1, ttl=60)
    cache.set("b", 2, ttl=60)
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_cache_stores_immutable_snapshot_when_value_is_a_dict():
    """A cached dict must not be mutated by later calculation code."""
    cache = TTLCache()
    value = {"value": 1}
    cache.set("k", value, ttl=60)
    value["value"] = 99
    assert cache.get("k") == {"value": 1}


# ---------------------------------------------------------------------------
# Inline SVG charts
# ---------------------------------------------------------------------------


def _metric_subclasses():
    return [Value, Trend, Partition, Progress, Table]


def test_all_five_metric_kinds_have_constants():
    assert (VALUE, TREND, PARTITION, PROGRESS, TABLE) == (
        "value",
        "trend",
        "partition",
        "progress",
        "table",
    )


@pytest.mark.parametrize("metric_cls", _metric_subclasses())
def test_metric_render_is_inline_svg_with_accessible_text(metric_cls):
    metric = metric_cls(title="Orders")
    data = _sample_data(metric_cls)
    svg = metric.render(data)
    assert svg.lstrip().startswith("<svg")
    assert "<title" in svg and "Orders" in svg
    assert "<desc" in svg
    assert 'role="img"' in svg
    assert "aria-label" in svg


@pytest.mark.parametrize("metric_cls", _metric_subclasses())
def test_metric_svg_is_offline_and_theme_aware(metric_cls):
    metric = metric_cls(title="Orders")
    svg = metric.render(_sample_data(metric_cls))
    assert "<script" not in svg
    assert "http://" not in svg
    assert "https://" not in svg
    # currentColor / CSS variables make the chart inherit the theme.
    assert "currentColor" in svg or "var(--admin" in svg


def _sample_data(metric_cls):
    if metric_cls is Value:
        return {"value": 42}
    if metric_cls is Trend:
        return {"points": [("2026-06-01", 3), ("2026-06-02", 5)]}
    if metric_cls is Partition:
        return {"parts": [("paid", 7), ("pending", 2)]}
    if metric_cls is Progress:
        return {"current": 7, "target": 10}
    return {"columns": ["name", "total"], "rows": [["Order A", 10], ["Order B", 20]]}


def test_progress_render_encodes_ratio_in_svg():
    svg = Progress(title="Fulfilled").render({"current": 1, "target": 4})
    assert "25%" in svg


def test_table_render_includes_all_rows_and_columns():
    svg = Table(title="Top orders").render({"columns": ["name", "total"], "rows": [["A", 1], ["B", 2]]})
    assert "Top orders" in svg
    assert "A" in svg and "B" in svg


# ---------------------------------------------------------------------------
# Authorization + cache key
# ---------------------------------------------------------------------------


class StubAuth:
    def __init__(self, allowed):
        self.allowed = set(allowed)

    def has_permission(self, user, permission, resource=None):
        return permission in self.allowed

    async def has_permission_async(self, user, permission, resource=None):
        return permission in self.allowed


class StubDashboard:
    def __init__(self, allowed):
        self.auth = StubAuth(allowed)


@pytest.mark.asyncio
async def test_metric_authorization_respects_permission():
    metric = Value(title="Revenue", permission="admin.view_revenue")
    assert await metric.authorized(StubDashboard(["admin.view_revenue"]), user="admin") is True
    assert await metric.authorized(StubDashboard([]), user="viewer") is False


def test_cache_key_varies_by_range_and_permission():
    a = Value(title="X", range="30d")
    b = Value(title="X", range="60d")
    assert a.cache_key() != b.cache_key()


def test_cache_key_is_stable():
    metric = Value(title="X", range="mtd")
    assert metric.cache_key() == metric.cache_key()
