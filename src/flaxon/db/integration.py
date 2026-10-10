"""Application-local Tortoise configuration and connection lifecycle."""

from __future__ import annotations

import importlib.util
from contextlib import contextmanager
from typing import Any

from tortoise.context import TortoiseContext, _current_context


def optional_module(name: str) -> bool:
    """Perform the optional module operation for this subsystem."""
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError as exc:
        if exc.name == name or name.startswith(f"{exc.name}."):
            return False
        raise


class Database:
    """One isolated database context per Flaxon application, never a global fallback."""

    def __init__(self, app: Any, settings: Any) -> None:
        self.app = app
        self.settings = settings
        self.context = TortoiseContext()
        self.initialized = False

    def configuration(self) -> dict[str, Any]:
        """Perform the configuration operation for database."""
        apps = {}
        if optional_module("models"):
            apps["models"] = {
                "models": ["models"],
                "default_connection": "default",
                "migrations": "migrations",
            }
        for module in getattr(self.app, "_orm_modules", []):
            if not module.models_module:
                continue
            if module.name in apps:
                raise ValueError(f"Duplicate ORM app label: {module.name}")
            apps[module.name] = {
                "models": [module.models_module],
                "default_connection": "default",
                "migrations": module.migrations_module
                or f"{module.models_module.rsplit('.', 1)[0]}.migrations",
            }
        if getattr(self.settings, "ADMIN_STORE_BACKEND", "sqlite") == "orm":
            apps["flaxon_admin"] = {
                "models": ["flaxon.db.storemodels"],
                "default_connection": "default",
                "migrations": "admin_migrations",
            }
        if not apps:
            raise ValueError("Create models.py or declare models_module on a mounted FlaxonModule")
        return {
            "connections": {"default": self.settings.DATABASE_URL},
            "apps": apps,
            "use_tz": True,
            "timezone": self.settings.TIME_ZONE,
        }

    @contextmanager
    def bind(self):
        # Tortoise 1.1 uses a ContextVar. Set/reset with a local token rather than
        # sharing Context.__enter__'s token between concurrent ASGI requests.
        """Bind the supplied values to this object's context."""
        token = _current_context.set(self.context)
        try:
            yield self.context
        finally:
            _current_context.reset(token)

    async def initialize(self) -> None:
        """Prepare the configured resources for use."""
        self.settings.prepare_database_directory()
        with self.bind():
            await self.context.init(config=self.configuration())
        self.initialized = True

    async def close(self) -> None:
        """Release the resources held by this object."""
        with self.bind():
            await self.context.close_connections()
        self.initialized = False

    async def __aenter__(self):
        await self.initialize()
        self._binding = self.bind()
        self._binding.__enter__()
        return self

    async def __aexit__(self, *args):
        try:
            await self.close()
        finally:
            self._binding.__exit__(*args)


class DatabaseMiddleware:
    """Database middleware implementation for the db subsystem."""

    def __init__(self, app: Any, database: Database) -> None:
        self.app = app
        self.database = database

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        with self.database.bind():
            await self.app(scope, receive, send)
