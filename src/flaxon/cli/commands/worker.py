from __future__ import annotations

import argparse
from typing import Any

from flaxon.cli.base import Command


class WorkerCommand(Command):
    def __init__(self) -> None:
        super().__init__(
            name="worker",
            handler=self._run,
            help_text="Run a background task worker",
            description="Start a worker process for background tasks",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("application", help="Application import string, e.g., app:app")
        parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent workers")
        parser.add_argument("--queue", default="default", help="Queue name to process")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        console.info(f"Starting worker for queue: {args.queue}")
        console.info(f"Concurrency: {args.concurrency}")

        try:
            from flaxon.utils.import_string import import_string
            app = import_string(args.application)
            console.info(f"Loaded application: {app.name}")

            import asyncio

            from flaxon.tasks import Worker
            from flaxon.tasks.registry import TaskRegistry

            registry = TaskRegistry()
            worker = Worker(registry, concurrency=args.concurrency, queue_name=args.queue)

            console.info("Worker started. Press Ctrl+C to stop.")

            try:
                # Worker installs its own SIGINT/SIGTERM handler and shuts
                # itself down internally, so start() usually just returns
                # normally on Ctrl+C rather than raising KeyboardInterrupt.
                asyncio.run(worker.start())
                console.info("\nWorker stopped.")
            except KeyboardInterrupt:
                console.info("\nShutting down worker...")
                asyncio.run(worker.stop())

            return 0

        except Exception as exc:
            console.error(f"Failed to start worker: {exc}")
            return 1
