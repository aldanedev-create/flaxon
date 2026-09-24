"""
Route grouping for Flaxon.

This module provides route grouping functionality for organizing routes
with common prefixes, middleware, and dependencies.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .router import Router


class RouteGroup:
    """
    Route group for organizing routes with common settings.

    Route groups allow you to group related routes with a common prefix,
    middleware, or dependencies.

    Example:
        ```python
        group = RouteGroup(prefix="/api/v1")

        @group.get("/users")
        async def list_users():
            return [{"id": 1}]

        @group.post("/users")
        async def create_user(data: CreateUser):
            return {"success": True}

        app.include_router(group)
        ```
    """

    def __init__(
        self,
        prefix: str = "",
        *,
        middleware: list[type] | None = None,
        dependencies: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the route group.

        Args:
            prefix: URL prefix for all routes in this group.
            middleware: List of middleware classes to apply to all routes.
            dependencies: Dependencies to inject into all routes.
        """
        self.router = Router(prefix=prefix)
        self.middleware = middleware or []
        self.dependencies = dependencies or {}

    def route(
        self,
        path: str,
        *,
        methods: set[str] | list[str] | tuple[str, ...] = ("GET",),
        name: str | None = None,
        **metadata: Any,
    ) -> Callable:
        """Register a route with custom methods."""
        return self.router.route(path, methods=methods, name=name, **metadata)

    def get(self, path: str, *, name: str | None = None, **metadata: Any) -> Callable:
        """Register a GET route."""
        return self.router.get(path, name=name, **metadata)

    def post(self, path: str, *, name: str | None = None, **metadata: Any) -> Callable:
        """Register a POST route."""
        return self.router.post(path, name=name, **metadata)

    def put(self, path: str, *, name: str | None = None, **metadata: Any) -> Callable:
        """Register a PUT route."""
        return self.router.put(path, name=name, **metadata)

    def patch(self, path: str, *, name: str | None = None, **metadata: Any) -> Callable:
        """Register a PATCH route."""
        return self.router.patch(path, name=name, **metadata)

    def delete(self, path: str, *, name: str | None = None, **metadata: Any) -> Callable:
        """Register a DELETE route."""
        return self.router.delete(path, name=name, **metadata)

    def head(self, path: str, *, name: str | None = None) -> Callable:
        """Register a HEAD route."""
        return self.router.head(path, name=name)

    def options(self, path: str, *, name: str | None = None) -> Callable:
        """Register an OPTIONS route."""
        return self.router.options(path, name=name)

    def websocket(self, path: str, *, name: str | None = None) -> Callable:
        """Register a WebSocket route."""
        return self.router.websocket(path, name=name)

    def include_router(self, router: Router, prefix: str | None = None) -> None:
        """Include routes from another router."""
        self.router.include_router(router, prefix=prefix)

    def add_middleware(self, middleware_class: type, **options: Any) -> None:
        """Add middleware to this group."""
        self.middleware.append(middleware_class)

    def as_router(self) -> Router:
        """
        Convert the group to a router.

        Returns:
            The router with all routes registered.
        """
        return self.router


class SubRouter(RouteGroup):
    """Alias for RouteGroup for clarity when creating sub-routers."""

    pass
