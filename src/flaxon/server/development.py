"""Development server implementation for running applications locally."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from flaxon._imports import import_module

from .configuration import ServerConfig
from .reload import Reloader


def _get_uvicorn() -> Any:
    """Lazy import for optional uvicorn dependency."""
    try:
        return import_module("uvicorn")

    except ImportError as exc:
        raise RuntimeError(
            "uvicorn is required to run the server. Install with: pip install uvicorn"
        ) from exc


class DevelopmentServer:
    """Development server managing application serving and hot reloading."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.reloader = Reloader() if config.reload else None
        self._task: asyncio.Task[None] | None = None

    def run(self, app: Any) -> None:
        """Run the development server synchronously in an event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.run_async(app))
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()

    async def run_async(self, app: Any) -> None:
        """Run the development server asynchronously."""
        uvicorn = _get_uvicorn()

        if self.reloader:
            self.reloader.start_watching()

        config = uvicorn.Config(
            app,
            host=self.config.host,
            port=self.config.port,
            log_level=self.config.log_level,
            reload=False,
            workers=1,
            loop="asyncio",
        )
        server = uvicorn.Server(config)

        self._task = asyncio.create_task(server.serve())

        try:
            await self._task
        except asyncio.CancelledError:
            await server.shutdown()
            raise

    async def stop(self) -> None:
        """Stop the running server task gracefully."""
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
