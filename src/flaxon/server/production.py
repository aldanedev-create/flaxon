from __future__ import annotations

import asyncio
import signal
from typing import Any

from flaxon._imports import import_module

from .configuration import ServerConfig
from .processes import ProcessManager


class ProductionServer:
    """Production server implementation for the server subsystem."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.process_manager = ProcessManager(config.workers)

    def run(self, app: Any) -> None:
        """Run the configured operation."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.run_async(app))
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()

    async def run_async(self, app: Any) -> None:
        """Perform the run async operation for production server."""
        uvicorn = import_module("uvicorn")

        if self.config.workers > 1:
            self.process_manager.start(app, self.config)

            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self._handle_shutdown)

            try:
                while self.process_manager.is_running():
                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                self._handle_shutdown()

        else:
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

            try:
                await server.serve()
            except KeyboardInterrupt:
                await server.shutdown()

    def _handle_shutdown(self) -> None:
        self.process_manager.stop()
