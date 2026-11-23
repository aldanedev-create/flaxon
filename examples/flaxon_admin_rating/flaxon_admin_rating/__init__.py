"""A complete example Flaxon admin extension: star ratings.

The package contributes four things, all built from Teloce ``.vel`` components:

* ``RatingField`` - a 1-5 star control for any integer model column.
* ``RatingCard`` - a dashboard card with the average and distribution.
* ``ratings`` page - every registered model that uses ``RatingField``.
* ``Rating insights`` tool - a dashboard shortcut to that page.

Install it with ``pip install -e examples/flaxon_admin_rating`` and the
``flaxon.admin`` entry point in ``pyproject.toml`` makes it appear automatically.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flaxon.admin import AdminExtension, Component, ExtensionPage, TeloceCard, TeloceField, Tool
from flaxon.validation import IntField

__all__ = ["RatingCard", "RatingExtension", "RatingField", "rating_distribution"]

_UI = Path(__file__).resolve().parent / "ui"
_MAX_STARS = 5


def _component(name: str) -> Component:
    return Component(name, _UI / f"{name}.vel")


class RatingField(TeloceField):
    """A five-star rating field validated as an integer from 1 to 5."""

    def __init__(self, name: str, **options: Any) -> None:
        options.setdefault("fallback", "select")
        options.setdefault(
            "fallback_choices",
            [(value, f"{value} of {_MAX_STARS}") for value in range(1, _MAX_STARS + 1)],
        )
        options.setdefault("props", {"max": _MAX_STARS, "stars": list(range(1, _MAX_STARS + 1))})
        super().__init__(name, _component("rating"), **options)

    def validation_field(self) -> Any:
        """Validate exactly like an API integer field with 1-5 bounds."""
        return IntField(
            required=self.required,
            default=self.default,
            minimum=1,
            maximum=_MAX_STARS,
        )


def rating_distribution(model: Any, field: str = "rating") -> Any:
    """Return ``{average, total, buckets}`` for one model, aggregated in SQL."""

    async def calculate() -> dict[str, Any]:
        from tortoise.functions import Count  # noqa: PLC0415 - optional dependency

        rows = (
            await model.filter(**{f"{field}__gt": 0})
            .group_by(field)
            .annotate(total=Count("id"))
            .values(field, "total")
        )
        counts = {value: 0 for value in range(1, _MAX_STARS + 1)}
        total = 0
        weighted = 0
        for row in rows:
            value = int(row[field])
            count = int(row["total"])
            counts[value] = count
            total += count
            weighted += value * count
        average = round(weighted / total, 2) if total else 0
        buckets = [
            {"value": value, "count": counts[value], "label": f"{value} star"}
            for value in range(1, _MAX_STARS + 1)
        ]
        max_count = max(counts.values(), default=0)
        return {
            "average": average,
            "average_label": f"{average:.1f}",
            "total": total,
            "buckets": buckets,
            "max_count": max_count,
            "field": field,
        }

    return calculate()


class RatingCard(TeloceCard):
    """Dashboard card: average rating and the 1-5 star distribution."""

    def __init__(self, model: Any, *, field: str = "rating", title: str | None = None, **options: Any) -> None:
        self.field_name = field
        super().__init__(
            title or f"Average {field.replace('_', ' ')}",
            _component("rating-summary"),
            calculate=self._calculate,
            model=model,
            **options,
        )

    async def _calculate(self, request: Any = None, *, now: Any = None) -> dict[str, Any]:
        return await rating_distribution(self.model, self.field_name)


class RatingPage(ExtensionPage):
    """A page listing every model that uses :class:`RatingField`."""

    def __init__(self) -> None:
        super().__init__(
            "ratings",
            _component("ratings"),
            label="Rating insights",
            icon="fa-star",
            permission="admin.view_ratings",
            category="Extensions",
            description="Average rating and distribution for every rated model.",
            props=self._props,
        )

    async def _props(self, request: Any) -> dict[str, Any]:
        dashboard = self._dashboard
        rows = []
        for admin_model in dashboard.registry.get_all():
            resource = getattr(admin_model, "resource", None)
            if resource is None:
                continue
            rated = [field for field in resource.fields if isinstance(field, RatingField)]
            if not rated:
                continue
            model = getattr(admin_model.model, "orm_model", admin_model.model)
            data = await rating_distribution(model, rated[0].name)
            rows.append(
                {
                    "name": admin_model.get_name(),
                    "label": admin_model.get_verbose_name_plural(),
                    "url": f"{dashboard.url_prefix}/{admin_model.get_name()}",
                    "average": data["average"],
                    "average_label": data["average_label"],
                    "total": data["total"],
                    "buckets": data["buckets"],
                    "max_count": data["max_count"],
                    "summary": ", ".join(f"{bucket['value']}★ {bucket['count']}" for bucket in data["buckets"]),
                }
            )
        return {"models": rows, "notes": [] if rows else ["No registered model uses the rating field yet."]}


class RatingExtension(AdminExtension):
    """Entry point target for the ``flaxon.admin`` group."""

    name = "rating"
    label = "Ratings"
    description = "Star-rating field, dashboard card and insights page."
    version = "0.1.0"

    def __init__(self) -> None:
        super().__init__()
        self._page = RatingPage()

    def setup(self, dashboard: Any) -> None:
        """Register the dedicated permission the insights page requires."""
        dashboard.register_permission(
            "admin.view_ratings",
            "View rating insights",
            category="Extensions",
            description="Open the rating insights page contributed by flaxon-admin-rating.",
        )

    def fields(self) -> list[type[RatingField]]:
        """Contribute the rating field class."""
        return [RatingField]

    def pages(self) -> list[ExtensionPage]:
        """Contribute the insights page."""
        return [self._page]

    def tools(self) -> list[Tool]:
        """Contribute the dashboard shortcut."""
        return [
            Tool(
                "Rating insights",
                self._page,
                icon="fa-star",
                description="See the average rating for every rated model.",
            )
        ]

    def model_registered(self, dashboard: Any, admin_model: Any) -> None:
        """Add one card per model that declares a :class:`RatingField`."""
        resource = getattr(admin_model, "resource", None)
        if resource is None:
            return
        for field in resource.fields:
            if not isinstance(field, RatingField):
                continue
            title = f"Average {field.label.lower()}"
            model = getattr(admin_model.model, "orm_model", admin_model.model)
            if any(isinstance(metric, RatingCard) and metric.model is model for metric in dashboard.metrics):
                return
            dashboard.register_metric(
                RatingCard(model, field=field.name, title=title, description="1-5 stars")
            )
            return
