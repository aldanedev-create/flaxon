from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

from ..base import Command
from ..generator import Generator


class NewCommand(Command):
    def __init__(self) -> None:
        super().__init__(
            name="new",
            handler=self._run,
            help_text="Create a new Flaxon project",
            description="Generate a starter Flaxon project",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("directory", help="Project directory name")
        parser.add_argument(
            "--template",
            default="fullstack",
            choices=["fullstack", "basic"],
            help="Project template (default: modular Teloce full-stack app)",
        )
        parser.add_argument("--no-venv", action="store_true", help="Skip virtual environment creation")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        directory = Path(args.directory)
        if directory.exists():
            console.error(f"Directory '{args.directory}' already exists")
            return 1

        console.info(f"Creating Flaxon project: {args.directory}")

        generator = Generator()

        try:
            generator.generate(directory, args.template)

            if not args.no_venv:
                console.info("Creating virtual environment...")
                import subprocess

                subprocess.run([sys.executable, "-m", "venv", ".venv"], cwd=directory, check=True)

            console.success(f"Project created at {directory.resolve()}")
            console.info("\nNext steps:")
            console.info(f"  cd {args.directory}")
            if not args.no_venv:
                console.info("  source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate")
            console.info("  python -m pip install -e .")
            if args.template == "fullstack":
                console.info("  flaxon welcome")
                console.info("  python management.py migrate")
                console.info("  python management.py setup-admin")
            console.info("  flaxon run app:app --reload")
            return 0

        except Exception as exc:
            console.error(f"Failed to create project: {exc}")
            return 1
