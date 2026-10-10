from __future__ import annotations

import asyncio
from typing import Any

from .configuration import ServerConfig
from .development import DevelopmentServer
from .production import ProductionServer


def run(
    app: Any,
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    reload: bool = False,
    workers: int = 1,
    env: str = "development",
    log_level: str = "info",
    **kwargs: Any,
) -> None:
    """Run the configured operation."""
    config = ServerConfig(
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        env=env,
        log_level=log_level,
        **kwargs,
    )

    server = ProductionServer(config) if env == "production" else DevelopmentServer(config)

    server.run(app)


def run_async(
    app: Any,
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    reload: bool = False,
    workers: int = 1,
    env: str = "development",
    log_level: str = "info",
    **kwargs: Any,
) -> asyncio.Task:
    """Perform the run async operation for this subsystem."""
    config = ServerConfig(
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        env=env,
        log_level=log_level,
        **kwargs,
    )

    server = ProductionServer(config) if env == "production" else DevelopmentServer(config)

    return asyncio.create_task(server.run_async(app))
