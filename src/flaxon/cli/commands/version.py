from __future__ import annotations

import argparse
import platform
import sys
from typing import Any

from flaxon._imports import import_attribute
from flaxon.cli.base import Command


class VersionCommand(Command):
    """Version command implementation for the cli subsystem."""

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
        __version__ = import_attribute("flaxon", "__version__")

        if args.short:
            print(__version__)
        else:
            console.info(f"Flaxon version: {__version__}")

            try:
                console.info(f"Python: {sys.version}")
                console.info(f"Platform: {platform.platform()}")
            except OSError:
                console.warning("Platform details unavailable")

        return 0
