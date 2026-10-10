from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from flaxon._imports import import_attribute, import_module
from flaxon.cli.base import Command


class RunCommand(Command):
    """Run command implementation for the cli subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="run",
            handler=self._run,
            help_text="Run a Flaxon ASGI application",
            description="Run a Flaxon application using Uvicorn",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("application", help="Application import string, e.g., app:app")
        parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
        parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
        parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
        parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
        parser.add_argument("--log-level", default="info", help="Log level")
        parser.add_argument("--env-file", help="Environment file to load")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        try:
            uvicorn = import_module("uvicorn")
        except ImportError:
            console.error("Uvicorn is not installed. Run: pip install uvicorn")
            return 1

        if args.env_file:
            load_dotenv = import_attribute("dotenv", "load_dotenv")

            load_dotenv(args.env_file)

        cwd = str(Path.cwd())
        if cwd not in sys.path:
            sys.path.insert(0, cwd)

        console.info(f"Starting Flaxon application: {args.application}")
        console.info(f"Host: {args.host}, Port: {args.port}")

        try:
            uvicorn.run(
                args.application,
                host=args.host,
                port=args.port,
                reload=args.reload,
                workers=args.workers,
                log_level=args.log_level,
                app_dir=cwd,
            )
            return 0
        except KeyboardInterrupt:
            console.info("\nShutting down...")
            return 0
        except Exception as exc:
            console.error(f"Failed to run application: {exc}")
            return 1
