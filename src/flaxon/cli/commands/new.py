from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from flaxon.cli.base import Command
from flaxon.cli.generator import Generator


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
                self._create_environment(directory, console)

            console.success(f"Project created at {directory.resolve()}")
            console.info("\nNext steps:")
            console.info(f"  cd {args.directory}")
            if not args.no_venv:
                console.info("  source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate")
            console.info("  python -m pip install -e .")
            if args.template == "fullstack":
                console.info("  flaxon welcome")
                console.info("  python management.py makemigrations")
                console.info("  python management.py migrate")
                console.info("  python management.py setup-admin")
            console.info("  flaxon run app:app --reload")
            return 0

        except subprocess.TimeoutExpired:
            console.error("Environment setup exceeded 120 seconds. The project files are ready.")
            console.info(f"  cd {args.directory}")
            console.info("  python -m venv .venv  # Retry environment setup separately")
            console.info("  # Use --no-venv when generating inside an active environment.")
            return 1
        except Exception as exc:
            console.error(f"Failed to create project: {exc}")
            return 1

    @staticmethod
    def _create_environment(directory: Path, console: Any) -> None:
        """Keep slow ensurepip work visible and bound the subprocess lifetime."""
        command = [sys.executable, "-m", "venv", ".venv"]
        process = subprocess.Popen(command, cwd=directory)
        started = time.monotonic()
        try:
            while True:
                elapsed = time.monotonic() - started
                remaining = 120 - elapsed
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, 120)
                try:
                    code = process.wait(timeout=min(3, remaining))
                    if code:
                        raise subprocess.CalledProcessError(code, command)
                    return
                except subprocess.TimeoutExpired:
                    if time.monotonic() - started >= 120:
                        raise
                    console.info("Still creating the environment (Python is installing pip)...")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
