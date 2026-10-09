from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Any

from flaxon.cli.base import Command


class BuildCommand(Command):
    def __init__(self) -> None:
        super().__init__(
            name="build",
            handler=self._run,
            help_text="Build distribution packages",
            description="Build wheel and source distribution",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--format", choices=["wheel", "sdist", "all"], default="all", help="Build format")
        parser.add_argument("--output", help="Output directory")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        cmd = [sys.executable, "-m", "build"]

        if args.output:
            cmd.extend(["--outdir", args.output])

        if args.format == "wheel":
            cmd.append("--wheel")
        elif args.format == "sdist":
            cmd.append("--sdist")

        console.info(f"Building: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd)
            if result.returncode == 0:
                console.success("Build completed successfully")
            return result.returncode
        except FileNotFoundError:
            console.error("build is not installed. Run: pip install build")
            return 1
