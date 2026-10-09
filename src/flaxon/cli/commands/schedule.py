from __future__ import annotations

import argparse
from typing import Any

from ..base import Command


class ScheduleCommand(Command):
    def __init__(self) -> None:
        super().__init__(
            name="schedule",
            handler=self._run,
            help_text="Run scheduled tasks",
            description="Execute scheduled tasks",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("application", help="Application import string, e.g., app:app")
        parser.add_argument("--once", action="store_true", help="Run once and exit")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        console.info("Starting scheduler...")

        try:
            from flaxon.utils.import_string import import_string
            app = import_string(args.application)
            console.info(f"Loaded application: {app.name}")

            import asyncio

            from flaxon.tasks import Scheduler
            from flaxon.tasks.queue import TaskQueue

            queue = TaskQueue()
            scheduler = Scheduler(queue)

            async def run_once() -> None:
                console.info("Running one scheduling pass...")
                await scheduler.run_once()

            async def run_forever() -> None:
                await scheduler.start()
                console.info("Scheduler started. Press Ctrl+C to stop.")
                try:
                    # start() only spawns the background loop and returns
                    # immediately, so something has to keep this coroutine
                    # (and therefore the event loop) alive until Ctrl+C.
                    while True:
                        await asyncio.sleep(3600)
                finally:
                    await scheduler.stop()

            try:
                if args.once:
                    asyncio.run(run_once())
                else:
                    asyncio.run(run_forever())
            except KeyboardInterrupt:
                console.info("\nShutting down scheduler...")

            return 0

        except Exception as exc:
            console.error(f"Failed to start scheduler: {exc}")
            return 1
