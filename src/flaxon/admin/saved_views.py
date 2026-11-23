"""Saved views: per-user, per-resource named query strings.

A saved view is just a query string, so applying one is a redirect to the list
URL. That keeps the URL the single source of truth and makes saved views
compose with filters, lenses and pagination. Views are namespaced by username:
one user can never read or delete another user's view (IDOR).
"""

from __future__ import annotations

import builtins
import re
import time
from typing import Any

__all__ = ["SavedView", "SavedViewStore"]

_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_NAMESPACE = "saved_views"
MAX_VIEWS = 50
MAX_NAME = 80
MAX_QUERY = 2000


def slugify(name: str) -> str:
    """Return a URL-safe slug for a view name."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(name).strip().lower()).strip("-")
    return slug[:60]


class SavedView:
    """A named query string owned by one user and one resource."""

    def __init__(self, name: str, query: str, *, created_at: float | None = None) -> None:
        self.name = name
        self.query = query
        self.created_at = created_at or time.time()

    @property
    def slug(self) -> str:
        """Return the URL slug derived from the display name."""
        return slugify(self.name)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {"name": self.name, "query": self.query, "created_at": self.created_at}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SavedView:
        """Rebuild a view from its stored representation."""
        return cls(str(data.get("name", "")), str(data.get("query", "")), created_at=data.get("created_at"))


class SavedViewStore:
    """Store saved views on the dashboard's AdminStore (or in memory)."""

    def __init__(self, dashboard: Any) -> None:
        self.dashboard = dashboard
        self._memory: dict[str, list[dict[str, Any]]] = {}

    def _key(self, username: str, model: str) -> str:
        return f"{username}:{model}"

    def list(self, username: str, model: str) -> builtins.list[SavedView]:
        """Return this user's views for ``model``."""
        raw: Any = None
        if self.dashboard.store is not None:
            raw = self.dashboard.store.get(_NAMESPACE, self._key(username, model), None)
        if raw is None:
            raw = self._memory.get(self._key(username, model), [])
        items = raw if isinstance(raw, builtins.list) else []
        return [SavedView.from_dict(item) for item in items if isinstance(item, dict)]

    def _write(self, username: str, model: str, views: builtins.list[SavedView]) -> None:
        payload = [view.to_dict() for view in views]
        self._memory[self._key(username, model)] = payload
        if self.dashboard.store is not None:
            self.dashboard.store.set(_NAMESPACE, self._key(username, model), payload)

    def save(self, username: str, model: str, name: str, query: str) -> SavedView:
        """Create or replace a named view for this user."""
        name = str(name).strip()[:MAX_NAME]
        if not name:
            raise ValueError("A saved view needs a name")
        query = str(query or "").strip().lstrip("?")[:MAX_QUERY]
        views = [view for view in self.list(username, model) if view.slug != slugify(name)]
        views.append(SavedView(name, query))
        if len(views) > MAX_VIEWS:
            raise ValueError(f"At most {MAX_VIEWS} saved views per resource")
        self._write(username, model, views)
        return views[-1]

    def get(self, username: str, model: str, slug: str) -> SavedView | None:
        """Return one view by slug, or ``None`` when it is not this user's."""
        if not _SLUG.match(str(slug or "")):
            return None
        return next((view for view in self.list(username, model) if view.slug == slug), None)

    def delete(self, username: str, model: str, slug: str) -> bool:
        """Delete one view by slug; return whether anything was removed."""
        views = self.list(username, model)
        remaining = [view for view in views if view.slug != slug]
        if len(remaining) == len(views):
            return False
        self._write(username, model, remaining)
        return True
