"""
Application bootstrapping and initialization.

This module handles the bootstrap process for Flaxon applications,
including loading configuration, registering plugins, and setting up
the application environment.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .app import Flaxon


class Bootstrapper:
    """
    Application bootstrapper that handles initialization and setup.

    This class manages the bootstrap process including:
        - Loading configuration from multiple sources
        - Discovering and loading plugins
        - Setting up the application environment
        - Running startup hooks
    """

    def __init__(self) -> None:
        """Initialize the bootstrapper."""
        self._hooks: list[Callable[[Flaxon], None]] = []
        self._plugins: list[dict[str, Any]] = []

    def bootstrap(
        self,
        name: str,
        *,
        config: dict[str, Any] | None = None,
        debug: bool | None = None,
        auto_discover: bool = True,
    ) -> Flaxon:
        """
        Bootstrap a Flaxon application.

        Args:
            name: The application name.
            config: Optional configuration dictionary.
            debug: Enable debug mode.
            auto_discover: Auto-discover plugins and modules.

        Returns:
            A configured Flaxon application instance.
        """
        app = Flaxon(name, debug=debug, config=config)

        if auto_discover:
            self._discover_plugins(app)

        for hook in self._hooks:
            hook(app)

        return app

    def _discover_plugins(self, app: Flaxon) -> None:
        """Discover and load plugins."""
        try:
            import pkgutil

            import flaxon_plugins

            for _, module_name, _ in pkgutil.iter_modules(flaxon_plugins.__path__):
                try:
                    module = importlib.import_module(f"flaxon_plugins.{module_name}")
                    if hasattr(module, "setup"):
                        module.setup(app)
                        self._plugins.append({
                            "name": module_name,
                            "module": module,
                        })
                except Exception as exc:
                    logging.getLogger(__name__).warning("Isolated callback or cleanup failed (%s)", type(exc).__name__)
        except ImportError:
            pass

        for path in Path("plugins").glob("*.py"):
            try:
                spec = importlib.util.spec_from_file_location(
                    f"plugins.{path.stem}",
                    path,
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, "setup"):
                        module.setup(app)
                        self._plugins.append({
                            "name": path.stem,
                            "module": module,
                        })
            except Exception as exc:
                logging.getLogger(__name__).warning("Isolated callback or cleanup failed (%s)", type(exc).__name__)

    def add_hook(self, hook: Callable[[Flaxon], None]) -> None:
        """
        Add a bootstrap hook.

        Args:
            hook: A function that takes a Flaxon application and configures it.
        """
        self._hooks.append(hook)

    def get_plugins(self) -> list[dict[str, Any]]:
        """Get all discovered plugins."""
        return self._plugins.copy()


class ApplicationFactory:
    """Factory for creating Flaxon applications with common configurations."""

    @staticmethod
    def create_api_app(
        name: str = "api",
        *,
        debug: bool = False,
        cors_origins: list[str] | None = None,
        rate_limit: int = 60,
    ) -> Flaxon:
        """Create a pre-configured API application."""
        from flaxon.middleware import CORSMiddleware
        from flaxon.security import RateLimitMiddleware

        app = Flaxon(name, debug=debug)

        if cors_origins:
            app.add_middleware(
                CORSMiddleware,
                allowed_origins=cors_origins,
                allow_credentials=True,
            )

        if rate_limit > 0:
            app.add_middleware(
                RateLimitMiddleware,
                requests=rate_limit,
                window_seconds=60,
            )

        return app

    @staticmethod
    def create_web_app(
        name: str = "web",
        *,
        debug: bool = False,
        template_dir: str = "templates",
    ) -> Flaxon:
        """Create a pre-configured web application with templates."""
        from flaxon.jinax import Jinax

        app = Flaxon(name, debug=debug)

        app.use_templates(
            Jinax(
                template_dir,
                auto_reload=debug,
                strict_undefined=True,
            )
        )

        return app

    @staticmethod
    def create_micro_app(name: str = "micro") -> Flaxon:
        """Create a minimal micro-application."""
        return Flaxon(name, debug=False)


def bootstrap_app(
    name: str,
    *,
    config: dict[str, Any] | None = None,
    debug: bool | None = None,
    auto_discover: bool = True,
) -> Flaxon:
    """
    Convenience function to bootstrap a Flaxon application.

    Args:
        name: The application name.
        config: Optional configuration dictionary.
        debug: Enable debug mode.
        auto_discover: Auto-discover plugins.

    Returns:
        A configured Flaxon application.
    """
    bootstrapper = Bootstrapper()
    return bootstrapper.bootstrap(
        name,
        config=config,
        debug=debug,
        auto_discover=auto_discover,
    )
