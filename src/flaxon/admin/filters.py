"""Class-based admin filters with URL state.

Filters are declarative: a resource declares the fields it exposes, and the
change list renders a control for each one. State lives entirely in the query
string (``filter_<field>``, ``filter_<field>_from``/``_to``) so links, saved
views and lenses compose without server-side session state.

Two evaluation paths are supported:

* ``orm_q`` builds a Tortoise ``Q`` object, so ORM-backed admins filter in SQL.
* ``matches`` evaluates a plain Python mapping/object, so legacy in-memory
  admin models keep working.

Tortoise is imported lazily: a lean Flaxon app that never registers a filter
must not import the ORM.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from flaxon._imports import import_attribute

__all__ = [
    "BooleanFilter",
    "DateRangeFilter",
    "Filter",
    "SelectFilter",
    "apply_python_filters",
    "build_filters",
]

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _q(**kwargs: Any) -> Any:
    return import_attribute("tortoise.expressions", "Q")(**kwargs)


def _raw_value(obj: Any, field: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(field)
    getter = getattr(obj, "get", None)
    if callable(getter):
        return getter(field)
    return getattr(obj, field, None)


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


class Filter:
    """Base filter: one URL parameter, one field, one equality test."""

    kind = "base"

    def __init__(self, field: str, *, label: str | None = None) -> None:
        self.field = field
        self.label = label or field.replace("_", " ").title()

    @property
    def parameter(self) -> str:
        """Return the query-string key that carries this filter's state."""
        return f"filter_{self.field}"

    def raw(self, params: Any) -> Any:
        """Return the raw query-string value for this filter."""
        return params.get(self.parameter)

    def value(self, params: Any) -> Any:
        """Return the normalised value, or ``None`` when inactive."""
        raw = self.raw(params)
        return raw if raw not in (None, "") else None

    def active(self, params: Any) -> bool:
        """Return whether the request carries a usable value for this filter."""
        return self.value(params) is not None

    def orm_q(self, params: Any) -> Any | None:
        """Build a ``Q`` for ORM queries, or ``None`` when inactive."""
        value = self.value(params)
        return _q(**{self.field: value}) if value is not None else None

    def matches(self, obj: Any, params: Any) -> bool:
        """Evaluate the filter against a plain Python row."""
        value = self.value(params)
        if value is None:
            return True
        return str(_raw_value(obj, self.field)) == str(value)

    def describe(self, params: Any) -> str:
        """Return a short human description for the active filter chip."""
        value = self.value(params)
        return f"{self.label}: {value}" if value is not None else ""

    def context(self, params: Any) -> dict[str, Any]:
        """Return template-friendly state for the filter panel."""
        return {
            "kind": self.kind,
            "field": self.field,
            "label": self.label,
            "parameter": self.parameter,
            "value": self.value(params),
            "active": self.active(params),
        }


class SelectFilter(Filter):
    """A dropdown restricted to a fixed set of choices."""

    kind = "select"

    def __init__(self, field: str, choices: Any = (), *, label: str | None = None) -> None:
        super().__init__(field, label=label)
        self.choices = list(choices)

    def value(self, params: Any) -> Any:
        """Return the selected choice, ignoring values outside the allowed set."""
        raw = self.raw(params)
        if raw in (None, ""):
            return None
        return raw if raw in self.choices else None

    def context(self, params: Any) -> dict[str, Any]:
        """Return template-friendly state including the available choices."""
        return {
            **super().context(params),
            "choices": [{"value": choice, "label": str(choice)} for choice in self.choices],
        }


class BooleanFilter(Filter):
    """A three-state boolean filter: all, true, false."""

    kind = "boolean"

    def value(self, params: Any) -> bool | None:
        """Return ``True``/``False`` for recognised tokens, else ``None``."""
        raw = str(self.raw(params) or "").strip().lower()
        if raw in _TRUE:
            return True
        if raw in _FALSE:
            return False
        return None

    def matches(self, obj: Any, params: Any) -> bool:
        """Compare the row's truthiness against the requested state."""
        value = self.value(params)
        if value is None:
            return True
        return bool(_raw_value(obj, self.field)) is value

    def describe(self, params: Any) -> str:
        """Return a short description using yes/no wording."""
        value = self.value(params)
        return "" if value is None else f"{self.label}: {'yes' if value else 'no'}"


class DateRangeFilter(Filter):
    """A from/to date range over a date or datetime field."""

    kind = "date_range"

    def __init__(self, field: str, *, label: str | None = None) -> None:
        super().__init__(field, label=label)

    @property
    def parameter_from(self) -> str:
        """Return the query-string key for the lower bound."""
        return f"filter_{self.field}_from"

    @property
    def parameter_to(self) -> str:
        """Return the query-string key for the upper bound."""
        return f"filter_{self.field}_to"

    def bounds(self, params: Any) -> tuple[date | None, date | None]:
        """Return the parsed (from, to) dates, ignoring unparseable input."""
        return _as_date(params.get(self.parameter_from)), _as_date(params.get(self.parameter_to))

    def active(self, params: Any) -> bool:
        """Return whether at least one bound parses to a real date."""
        return any(bound is not None for bound in self.bounds(params))

    def orm_q(self, params: Any) -> Any | None:
        """Build an inclusive range ``Q`` using timezone-aware datetimes."""
        start, end = self.bounds(params)
        if start is None and end is None:
            return None
        query = None
        if start is not None:
            query = _q(**{f"{self.field}__gte": datetime(start.year, start.month, start.day, tzinfo=UTC)})
        if end is not None:
            upper = _q(**{
                f"{self.field}__lte": datetime(end.year, end.month, end.day, 23, 59, 59, 999999, tzinfo=UTC)
            })
            query = upper if query is None else query & upper
        return query

    def matches(self, obj: Any, params: Any) -> bool:
        """Compare the row's date against the inclusive bounds."""
        start, end = self.bounds(params)
        if start is None and end is None:
            return True
        value = _as_date(_raw_value(obj, self.field))
        if value is None:
            return False
        if start is not None and value < start:
            return False
        return not (end is not None and value > end)

    def context(self, params: Any) -> dict[str, Any]:
        """Return template-friendly state including both bound parameters."""
        start, end = self.bounds(params)
        return {
            **super().context(params),
            "parameter_from": self.parameter_from,
            "parameter_to": self.parameter_to,
            "value_from": start.isoformat() if start else "",
            "value_to": end.isoformat() if end else "",
        }


def build_filters(specs: Any) -> list[Filter]:
    """Normalise a mixed list of field names and filter objects."""
    built: list[Filter] = []
    for spec in specs or []:
        if isinstance(spec, Filter):
            built.append(spec)
        elif isinstance(spec, str):
            built.append(Filter(spec))
        else:
            raise TypeError(f"Unsupported filter specification: {spec!r}")
    return built


def apply_python_filters(filters: Any, params: Any, rows: list[Any]) -> list[Any]:
    """Apply every active filter to a list of plain Python rows."""
    selected = list(rows)
    for filt in build_filters(filters):
        if filt.active(params):
            selected = [row for row in selected if filt.matches(row, params)]
    return selected
