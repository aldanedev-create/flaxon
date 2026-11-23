# Metrics and dashboard cards

Flaxon Admin can render SQL-backed metric cards on the dashboard index and on
each model's change list. The five metric kinds are `Value`, `Trend`,
`Partition`, `Progress` and `Table`.

Metrics are **additive**: registration never changes the legacy
`register(Model, **options)` path. Every calculation runs as a SQL aggregate
through Tortoise (`count`, `annotate`/`group_by`), not a Python row loop. Charts
are inline SVG — no JavaScript, no CDN, theme-aware through `currentColor`, and
carrying a `<title>`/`<desc>` text alternative for assistive technology.

## A minimal metric

The example below is executed by
`tests/docs/test_admin_metrics_docs.py`. `Order` is any Tortoise model with a
`created_at` field.

```python
from flaxon.admin.metrics import Value

value = Value("Total orders", model=Order, range="30d", date_field="created_at")
dashboard.register_metric(value)
assert value.kind == "value"
```

`register_metric(metric, placement="dashboard")` places a card on the index.
Pass a registered model name to place it on that model's change list:

```python
dashboard.register_metric(value, placement="order")
assert value.placement == "order"
```

## The five metric kinds

Each class implements `calculate()` (SQL) and `render()` (inline SVG):

```python
from flaxon.admin.metrics import Partition, Progress, Table, Trend, Value

base = dict(model=Order, range="30d", date_field="created_at")
cards = [
    Value("Revenue", field="amount", aggregate="sum", **base),
    Trend("Orders per day", **base),
    Partition("Orders by status", field="status", **base),
    Progress("Fulfilled", current_filter={"fulfilled": True}, **base),
    Table("Top orders", columns=["reference", "amount"], limit=5, **base),
]
assert [card.kind for card in cards] == ["value", "trend", "partition", "progress", "table"]
```

The SVG from `render()` is offline and accessible. This is verified in a real
browser by `tests/browser/test_admin_metrics_browser.py`, which seeds a real
database and captures `assets/readme/admin-metrics.png`:

![Admin metrics dashboard](../assets/readme/admin-metrics.png)

## Ranges

`range` accepts `30d`, `60d`, `mtd`, `qtd`, `ytd` and `custom`. Ranges resolve to
UTC bounds that filter the SQL query.

```python
from datetime import datetime, timezone
from flaxon.admin.metrics import resolve_range

now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
qtd = resolve_range("qtd", now=now)
assert qtd.start.month == 4 and qtd.start.day == 1

custom = resolve_range("custom", now=now, start=now, end=now)
assert custom.start == custom.end == now
```

## Caching and invalidation

`cached_calculate()` stores results for `ttl` seconds (default 60). Change a
card's data and call `dashboard.invalidate_metrics()` to refresh the cards.

```python
from flaxon.admin.metrics import TTLCache

cache = TTLCache()
cache.set("orders:value", 7, ttl=60)
assert cache.get("orders:value") == 7
assert cache.invalidate("orders:") == 1
assert cache.get("orders:value") is None
```

## Authorization

Every metric defaults to the `admin.view_dashboard` permission. Override it
with `permission="..."` to hide a card from users without that capability —
unauthorized users never see the card and no calculation runs.
