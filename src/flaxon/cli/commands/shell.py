from __future__ import annotations

import argparse
import code
from typing import Any

from ..base import Command


class ShellCommand(Command):
    def __init__(self) -> None:
        super().__init__(
            name="shell",
            handler=self._run,
            help_text="Start an interactive Python shell",
            description="Launch a Python shell with the application context loaded",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("application", nargs="?", help="Application import string, e.g., app:app")
        parser.add_argument("--no-import", action="store_true", help="Skip importing the application")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        context = {}

        if args.application and not args.no_import:
            try:
                from flaxon.utils.import_string import import_string
                app = import_string(args.application)
                context["app"] = app
                context["Flaxon"] = app.__class__
                console.success(f"Loaded application: {app.name}")
            except Exception as exc:
                console.warning(f"Could not load application: {exc}")

        console.info("Starting Flaxon shell...")
        console.info(f"Available context: {list(context.keys()) if context else 'None'}")

        code.interact(local=context)
        return 0
