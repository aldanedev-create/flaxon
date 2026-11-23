"""Lenses: named alternate change lists with their own query and columns.

A lens is a lightweight, declarative view of a resource — "unpaid orders",
"today's signups" — that reuses the list view, filters and pagination. It is
addressed by name in the URL (``?lens=<name>``) so it can be bookmarked and
combined with saved views.
"""

from __future__ import annotations

import re
from typing import Any

from .filters import build_filters

__all__ = ["Lens"]

_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class Lens:
    """A named alternate index for a resource."""

    def __init__(
        self,
        name: Any,
        *,
        label: str | None = None,
        columns: list[str] | None = None,
        filters: Any = (),
        query: dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(name, str) or not _NAME.match(name):
            raise ValueError("Lens names must be lowercase slugs: [a-z0-9][a-z0-9_-]*")
        self.name = name
        self.label: str | None = label
        self.columns = list(columns or [])
        self.filters = build_filters(filters)
        self.query = dict(query or {})

    def get_label(self) -> str:
        """Return the human label, defaulting to the title-cased name."""
        return self.label or self.name.replace("-", " ").replace("_", " ").title()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Lens({self.name!r})"
