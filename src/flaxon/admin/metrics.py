"""Declarative, additive metrics and dashboard cards for the Flaxon admin.

Metrics aggregate with SQL (Tortoise ``count``/``annotate``/``group_by``) rather
than loading rows into Python. Charts are inline SVG: no JavaScript, no CDN,
theme-aware through ``currentColor``, and carrying a text alternative for
assistive technology.

The API is additive: nothing here changes the legacy ``register(...)`` path.
"""

from __future__ import annotations

import html
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from flaxon._imports import import_attribute

__all__ = [
    "PARTITION",
    "PROGRESS",
    "TABLE",
    "TREND",
    "VALUE",
    "Metric",
    "MetricRange",
    "Partition",
    "Progress",
    "TTLCache",
    "Table",
    "Trend",
    "Value",
    "resolve_range",
]

VALUE = "value"
TREND = "trend"
PARTITION = "partition"
PROGRESS = "progress"
TABLE = "table"

_VALID_RANGES = frozenset({"30d", "60d", "mtd", "qtd", "ytd", "custom"})


# ---------------------------------------------------------------------------
# Ranges
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricRange:
    """A resolved, immutable time window for a metric calculation."""

    key: str
    start: datetime | None = None
    end: datetime | None = None


def _utc_now() -> datetime:
    return datetime.now(UTC)


def resolve_range(
    key: str,
    *,
    now: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> MetricRange:
    """Resolve a named range (30d/60d/mtd/qtd/ytd/custom) to concrete bounds."""
    if key not in _VALID_RANGES:
        raise ValueError(f"Unknown metric range: {key!r}")
    moment = now or _utc_now()
    if key == "custom":
        return MetricRange(key=key, start=start, end=end)
    if key in {"30d", "60d"}:
        days = 30 if key == "30d" else 60
        return MetricRange(key=key, start=moment - timedelta(days=days), end=moment)
    if key == "mtd":
        month_start = moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return MetricRange(key=key, start=month_start, end=moment)
    if key == "qtd":
        quarter_start_month = ((moment.month - 1) // 3) * 3 + 1
        return MetricRange(
            key=key,
            start=moment.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0),
            end=moment,
        )
    # ytd
    return MetricRange(
        key=key,
        start=moment.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0),
        end=moment,
    )


# ---------------------------------------------------------------------------
# TTL cache
# ---------------------------------------------------------------------------


class TTLCache:
    """A tiny in-process cache with per-entry TTL and prefix invalidation."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.monotonic
        self._entries: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        """Return the cached value for ``key`` or ``None`` when absent/expired."""
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._clock() >= expires_at:
            self._entries.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, *, ttl: float) -> None:
        """Store ``value`` under ``key`` for ``ttl`` seconds."""
        # Snapshot mutable containers so callers cannot mutate cached data.
        if isinstance(value, dict):
            value = dict(value)
        elif isinstance(value, list):
            value = list(value)
        self._entries[key] = (self._clock() + ttl, value)

    def invalidate(self, prefix: str | None = None) -> int:
        """Remove entries whose key starts with ``prefix``; return the count removed."""
        if prefix is None:
            return self.clear()
        matches = [key for key in self._entries if key.startswith(prefix)]
        for key in matches:
            self._entries.pop(key, None)
        return len(matches)

    def clear(self) -> int:
        """Remove every entry and return the number cleared."""
        count = len(self._entries)
        self._entries.clear()
        return count

    def __len__(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _fmt_number(value: Any) -> str:
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return str(value)


# Tortoise is an optional dependency. Import its helpers lazily so importing
# flaxon.admin (or a lean generated app) never pulls it into sys.modules.
def _tortoise(name: str, *, module: str = "tortoise.functions") -> Any:
    return import_attribute(module, name)


# ---------------------------------------------------------------------------
# Metric base
# ---------------------------------------------------------------------------


class Metric:
    """Base class for a dashboard card.

    Subclasses implement :meth:`calculate` (SQL aggregation) and :meth:`render`
    (inline SVG). ``date_field`` defaults to ``created_at`` and can be changed
    per metric. ``cached_calculate`` layers TTL caching on top.
    """

    kind: str = VALUE
    date_field: str = "created_at"

    def __init__(
        self,
        title: str,
        *,
        description: str = "",
        range: str = "30d",
        ttl: float = 60,
        permission: str = "admin.view_dashboard",
        date_field: str | None = None,
        model: Any = None,
        field: str | None = None,
        cache: TTLCache | None = None,
    ) -> None:
        self.title = title
        self.description = description
        self.range = range
        self.ttl = ttl
        self.permission = permission
        if date_field is not None:
            self.date_field = date_field
        self.model = model
        self.field = field
        self.cache = cache or TTLCache()
        self.placement: str = "dashboard"

    # -- range / filters ----------------------------------------------------
    def range_bounds(self, *, now: datetime | None = None) -> MetricRange:
        """Resolve this metric's configured range to concrete UTC bounds."""
        return resolve_range(self.range, now=now)

    def _range_filters(self, *, now: datetime | None = None) -> dict[str, Any]:
        bounds = self.range_bounds(now=now)
        filters: dict[str, Any] = {}
        if bounds.start is not None:
            filters[f"{self.date_field}__gte"] = bounds.start
        if bounds.end is not None:
            filters[f"{self.date_field}__lte"] = bounds.end
        return filters

    # -- caching ------------------------------------------------------------
    def cache_key(self) -> str:
        """Return a stable, collision-safe cache key for this card."""
        parts = (
            type(self).__name__,
            self.title,
            self.range,
            self.date_field,
            str(self.field or ""),
            str(getattr(self, "aggregate", "")),
        )
        return "|".join(parts)

    async def cached_calculate(self, request: Any = None, *, now: datetime | None = None) -> dict[str, Any]:
        """Calculate with TTL caching; reuse a fresh result until ``ttl`` expires."""
        key = self.cache_key()
        cached = self.cache.get(key)
        if cached is not None:
            return dict(cached)
        value = await self.calculate(request, now=now)
        self.cache.set(key, value, ttl=self.ttl)
        return value

    # -- authorization ------------------------------------------------------
    async def authorized(self, dashboard: Any, *, user: Any) -> bool:
        """Return whether ``user`` is allowed to see this card in ``dashboard``."""
        """Return whether ``user`` may see this card in ``dashboard``."""
        if user is None:
            return False
        provider = getattr(dashboard, "auth", dashboard)
        has_async = getattr(provider, "has_permission_async", None)
        if has_async is not None:
            return bool(await has_async(user, self.permission))
        has_sync = getattr(provider, "has_permission", None)
        if has_sync is not None:
            result = has_sync(user, self.permission)
            return bool(await result) if hasattr(result, "__await__") else bool(result)
        return False

    # -- contract hooks -----------------------------------------------------
    async def calculate(self, request: Any = None, *, now: datetime | None = None) -> dict[str, Any]:
        """Compute the metric data. Subclasses implement SQL aggregation here."""
        raise NotImplementedError

    def render(self, data: dict[str, Any]) -> str:
        """Render the calculated data as an inline, accessible SVG string."""
        raise NotImplementedError

    def _wrap(self, description: str, viewbox: str, body: str) -> str:
        label = f"{self.title} - {description}" if description else self.title
        return (
            f'<svg class="fx-metric" viewBox="{viewbox}" role="img" '
            f'aria-label="{_escape(label)}">'
            f"<title>{_escape(self.title)}</title>"
            f"<desc>{_escape(description or self.title)}</desc>"
            f"{body}</svg>"
        )


# ---------------------------------------------------------------------------
# Value
# ---------------------------------------------------------------------------


class Value(Metric):
    """A single aggregate number (count, sum, avg, min or max)."""

    kind = VALUE

    def __init__(self, title: str, *, aggregate: str = "count", **kwargs: Any) -> None:
        super().__init__(title, **kwargs)
        if aggregate not in {"count", "sum", "avg", "min", "max"}:
            raise ValueError(f"Unknown aggregate: {aggregate!r}")
        self.aggregate = aggregate

    async def calculate(self, request: Any = None, *, now: datetime | None = None) -> dict[str, Any]:
        """Aggregate a single value in SQL (count/sum/avg/min/max)."""
        query = self.model.filter(**self._range_filters(now=now))
        if self.aggregate == "count":
            value: Any = await query.count()
        else:
            if self.field is None:
                raise ValueError(f"aggregate={self.aggregate!r} requires a field")
            func_name = {"sum": "Sum", "avg": "Avg", "min": "Min", "max": "Max"}[self.aggregate]
            func = _tortoise(func_name)
            rows = await query.annotate(_agg=func(self.field)).values("_agg")
            value = rows[0]["_agg"] if rows else 0
        if isinstance(value, Decimal):
            value = float(value)
        return {"value": value}

    def render(self, data: dict[str, Any]) -> str:
        """Render the single value as a large inline SVG number."""
        value = _fmt_number(data.get("value", 0))
        detail = self.description or f"{self.aggregate} for the selected range"
        body = (
            f'<text x="110" y="52" text-anchor="middle" fill="currentColor" '
            f'font-size="34" font-weight="700">{_escape(value)}</text>'
        )
        return self._wrap(detail, "0 0 220 80", body)


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------


class Trend(Metric):
    """A daily time series rendered as an inline line chart."""

    kind = TREND

    async def calculate(self, request: Any = None, *, now: datetime | None = None) -> dict[str, Any]:
        """Group rows by day in SQL and return the daily time series."""
        raw_sql = _tortoise("RawSQL", module="tortoise.expressions")
        count = _tortoise("Count")
        field_meta = self.model._meta.fields_map.get(self.date_field)
        column = getattr(field_meta, "db_column", None) or self.date_field
        rows = (
            await self.model
            .filter(**self._range_filters(now=now))
            .annotate(day=raw_sql(f"DATE({column})"), cnt=count("id"))
            .group_by("day")
            .values("day", "cnt")
        )
        points = [(str(row["day"]), int(row["cnt"])) for row in rows]
        return {"points": points}

    def render(self, data: dict[str, Any]) -> str:
        """Render the daily points as an inline SVG line chart."""
        points = data.get("points", [])
        width, height, pad = 320, 120, 10
        parts: list[str] = []
        if points:
            counts = [count for _, count in points]
            highest = max(counts) or 1
            span = max(len(points) - 1, 1)
            coords = []
            for index, (_, count) in enumerate(points):
                x = pad + (index * (width - 2 * pad) // span)
                y = height - pad - (count / highest) * (height - 2 * pad)
                coords.append((x, y))
            polyline = " ".join(f"{x},{y:.1f}" for x, y in coords)
            parts.append(
                f'<polyline points="{polyline}" fill="none" stroke="currentColor" '
                f'stroke-width="2.5" stroke-linejoin="round"/>'
            )
            for x, y in coords:
                parts.append(f'<circle cx="{x}" cy="{y:.1f}" r="2.5" fill="currentColor"/>')
        detail = self.description or f"{len(points)} daily points"
        return self._wrap(detail, f"0 0 {width} {height}", "".join(parts))


# ---------------------------------------------------------------------------
# Partition
# ---------------------------------------------------------------------------


class Partition(Metric):
    """A breakdown by a field rendered as inline horizontal bars."""

    kind = PARTITION

    async def calculate(self, request: Any = None, *, now: datetime | None = None) -> dict[str, Any]:
        """Group rows by ``field`` in SQL and return category counts."""
        count = _tortoise("Count")
        rows = (
            await self.model
            .filter(**self._range_filters(now=now))
            .group_by(self.field)
            .annotate(cnt=count("id"))
            .values(self.field, "cnt")
        )
        parts = [(str(row[self.field]), int(row["cnt"])) for row in rows]
        return {"parts": parts}

    def render(self, data: dict[str, Any]) -> str:
        """Render the categories as inline SVG horizontal bars."""
        parts = data.get("parts", [])
        width, row_h = 280, 26
        height = max(len(parts), 1) * row_h + 8
        highest = max((count for _, count in parts), default=1) or 1
        parts_svg: list[str] = []
        for index, (label, count) in enumerate(parts):
            y = 4 + index * row_h
            bar_w = int((count / highest) * (width - 110))
            parts_svg.append(
                f'<text x="0" y="{y + 13}" fill="currentColor" font-size="11">{_escape(label)}</text>'
                f'<rect x="80" y="{y + 3}" width="{max(bar_w, 1)}" height="14" '
                f'fill="currentColor" opacity="0.75"/>'
                f'<text x="{width - 2}" y="{y + 14}" text-anchor="end" fill="currentColor" '
                f'font-size="11">{count}</text>'
            )
        detail = self.description or f"{len(parts)} categories"
        return self._wrap(detail, f"0 0 {width} {height}", "".join(parts_svg))


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------


class Progress(Metric):
    """A current/target ratio rendered as an inline progress bar."""

    kind = PROGRESS

    def __init__(self, title: str, *, current_filter: dict[str, Any] | None = None, **kwargs: Any) -> None:
        super().__init__(title, **kwargs)
        self.current_filter = current_filter or {}

    async def calculate(self, request: Any = None, *, now: datetime | None = None) -> dict[str, Any]:
        """Compute current/target counts in SQL and their ratio."""
        filters = self._range_filters(now=now)
        target = await self.model.filter(**filters).count()
        current = await self.model.filter(**filters, **self.current_filter).count()
        ratio = (current / target) if target else 0.0
        return {"current": current, "target": target, "ratio": ratio}

    def render(self, data: dict[str, Any]) -> str:
        """Render the ratio as an inline SVG progress bar."""
        current = int(data.get("current", 0))
        target = int(data.get("target", 0))
        ratio = data.get("ratio")
        if ratio is None:
            ratio = (current / target) if target else 0.0
        percent = round(ratio * 100)
        bar_w = 200
        filled = int(bar_w * percent / 100)
        label = f"{percent}%"
        body = (
            f'<rect x="0" y="18" width="{bar_w}" height="16" rx="8" '
            f'fill="currentColor" opacity="0.18"/>'
            f'<rect x="0" y="18" width="{filled}" height="16" rx="8" fill="currentColor"/>'
            f'<text x="{bar_w + 8}" y="31" fill="currentColor" font-size="13" '
            f'font-weight="700">{_escape(label)}</text>'
            f'<text x="0" y="12" fill="currentColor" font-size="10">'
            f"{current} / {target}</text>"
        )
        detail = self.description or f"{current} of {target}"
        return self._wrap(detail, "0 0 260 50", body)


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------


class Table(Metric):
    """A small tabular metric rendered with inline SVG text rows."""

    kind = TABLE

    def __init__(
        self,
        title: str,
        *,
        columns: list[str] | None = None,
        limit: int = 5,
        **kwargs: Any,
    ) -> None:
        super().__init__(title, **kwargs)
        self.columns = columns or []
        self.limit = max(1, min(int(limit), 50))

    async def calculate(self, request: Any = None, *, now: datetime | None = None) -> dict[str, Any]:
        """Return column names and bounded rows selected in SQL."""
        rows = await self.model.filter(**self._range_filters(now=now)).limit(self.limit).values(*self.columns)
        serializable = [[_fmt_number(row[column]) for column in self.columns] for row in rows]
        return {"columns": list(self.columns), "rows": serializable}

    def render(self, data: dict[str, Any]) -> str:
        """Render the rows as an inline SVG text table."""
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        line_h = 20
        width = 280
        height = (len(rows) + 1) * line_h + 6
        parts: list[str] = [
            f'<text x="0" y="14" fill="currentColor" font-size="11" font-weight="700">'
            f"{_escape(' | '.join(columns))}</text>"
        ]
        for index, row in enumerate(rows):
            y = 14 + (index + 1) * line_h
            parts.append(
                f'<text x="0" y="{y}" fill="currentColor" font-size="11">'
                f"{_escape(' | '.join(str(cell) for cell in row))}</text>"
            )
        detail = self.description or f"{len(rows)} rows"
        return self._wrap(detail, f"0 0 {width} {height}", "".join(parts))
