from __future__ import annotations

import asyncio
import multiprocessing
from typing import Any

from flaxon._imports import import_module


class WorkerProcess:
    """Worker process implementation for the server subsystem."""

    def __init__(self, index: int, app: Any, config: Any) -> None:
        self.index = index
        self.app = app
        self.config = config
        self.process: multiprocessing.Process | None = None

    def start(self) -> None:
        """Start the configured service."""
        self.process = multiprocessing.Process(
            target=self._run_worker,
            args=(self.index, self.app, self.config),
            daemon=True,
        )
        self.process.start()

    def _run_worker(self, index: int, app: Any, config: Any) -> None:
        uvicorn = import_module("uvicorn")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        uvicorn_config = uvicorn.Config(
            app,
            host=config.host,
            port=config.port,
            log_level=config.log_level,
            reload=False,
            workers=1,
            loop="asyncio",
        )
        server = uvicorn.Server(uvicorn_config)

        try:
            loop.run_until_complete(server.serve())
        except KeyboardInterrupt:
            loop.run_until_complete(server.shutdown())
        finally:
            loop.close()

    def stop(self) -> None:
        """Stop the configured service."""
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=10)
            if self.process.is_alive():
                self.process.kill()

    def is_alive(self) -> bool:
        """Return whether alive holds for the current value."""
        return self.process is not None and self.process.is_alive()


class ProcessManager:
    """Process manager implementation for the server subsystem."""

    def __init__(self, num_workers: int) -> None:
        self.num_workers = num_workers
        self.workers: list[WorkerProcess] = []
        self._running = False

    def start(self, app: Any, config: Any) -> None:
        """Start the configured service."""
        self._running = True

        for i in range(self.num_workers):
            worker = WorkerProcess(i, app, config)
            worker.start()
            self.workers.append(worker)

    def stop(self) -> None:
        """Stop the configured service."""
        self._running = False

        for worker in self.workers:
            worker.stop()

        self.workers.clear()

    def is_running(self) -> bool:
        """Return whether running holds for the current value."""
        return self._running and any(w.is_alive() for w in self.workers)

    def restart_worker(self, index: int, app: Any, config: Any) -> None:
        """Perform the restart worker operation for process manager."""
        if index < len(self.workers):
            self.workers[index].stop()
            self.workers[index] = WorkerProcess(index, app, config)
            self.workers[index].start()
