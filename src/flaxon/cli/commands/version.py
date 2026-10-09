from __future__ import annotations

import argparse
from typing import Any

from ..base import Command


class VersionCommand(Command):
    def __init__(self) -> None:
        super().__init__(
            name="version",
            handler=self._run,
            help_text="Show Flaxon version",
            description="Display the current Flaxon version",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--short", action="store_true", help="Show only version number")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        from flaxon import __version__

        if args.short:
            print(__version__)
        else:
            console.info(f"Flaxon version: {__version__}")

            try:
                import platform
                import sys
                console.info(f"Python: {sys.version}")
                console.info(f"Platform: {platform.platform()}")
            except OSError:
                console.warning("Platform details unavailable")

        return 0
