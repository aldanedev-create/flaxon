"""
Route mounting for Flaxon.

This module provides functionality for mounting sub-applications
and routers at specific paths.
"""

from __future__ import annotations

from typing import Any

from .router import Router


class Mount:
    """
    Mount a sub-application or router at a specific path.

    This allows you to mount entire applications or routers at a path prefix,
    useful for modularizing large applications.

    Example:
        ```python
        from flaxon import Flaxon
        from flaxon.routing import Mount

        admin_app = Flaxon("admin")

        @admin_app.get("/")
        async def admin_home():
            return {"admin": True}

        app = Flaxon("main")
        mount = Mount("/admin", admin_app)
        app.include_router(mount)
        ```
    """

    def __init__(
        self,
        path: str,
        app: Any,
        *,
        name: str | None = None,
        middleware: list[type] | None = None,
    ) -> None:
        """
        Initialize the mount.

        Args:
            path: The path prefix to mount at.
            app: The application or router to mount.
            name: Optional name for the mount.
            middleware: Middleware to apply to the mounted app.
        """
        self.path = path.rstrip("/") if path != "/" else "/"
        self.app = app
        self.name = name
        self.middleware = middleware or []
        self._router = Router(prefix=self.path)

    def as_router(self) -> Router:
        """
        Convert the mount to a router.

        Returns:
            A router with the mounted app's routes, prefixed with this mount's path.
        """
        if hasattr(self.app, "router"):
            http_routes = list(self.app.router.routes)
            websocket_routes = list(getattr(self.app.router, "websocket_routes", []))
        elif hasattr(self.app, "routes"):
            http_routes = list(self.app.routes)
            websocket_routes = []
        else:
            raise ValueError(f"Cannot mount object of type {type(self.app)}")

        for route in http_routes:
            self._router.route(
                route.path,
                methods=route.methods,
                name=route.name,
                summary=getattr(route, "summary", None),
                description=getattr(route, "description", None),
                tags=getattr(route, "tags", None),
                operation_id=getattr(route, "operation_id", None),
                responses=getattr(route, "responses", None),
                deprecated=getattr(route, "deprecated", False),
                security=getattr(route, "security", None),
            )(route.endpoint)

        for route in websocket_routes:
            self._router.websocket(route.path, name=route.name)(route.endpoint)

        return self._router


def mount(path: str, app: Any, *, name: str | None = None) -> Mount:
    """
    Convenience function for mounting an application.

    Args:
        path: The path prefix to mount at.
        app: The application or router to mount.
        name: Optional name for the mount.

    Returns:
        A Mount object.

    Example:
        ```python
        admin_app = Flaxon("admin")
        app = Flaxon("main")
        app.include_router(mount("/admin", admin_app))
        ```
    """
    return Mount(path, app, name=name)
