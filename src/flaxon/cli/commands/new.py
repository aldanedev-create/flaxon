from __future__ import annotations

import argparse
import math
import os
import shlex
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

from flaxon.cli.base import Command
from flaxon.cli.generator import Generator


def _timeout(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("timeout must be a positive number of seconds")
    return seconds


class NewCommand(Command):
    """Generate a project with visible, recoverable environment setup."""

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
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument(
            "--no-venv", action="store_true", help="Generate files only; use your own environment"
        )
        mode.add_argument(
            "--resume-venv",
            action="store_true",
            help="Finish environment setup in an existing project without rewriting files",
        )
        parser.add_argument(
            "--venv-timeout",
            type=_timeout,
            default=120.0,
            metavar="SECONDS",
            help="Timeout for each environment setup phase (default: 120 seconds)",
        )

    @staticmethod
    def _quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'" if os.name == "nt" else shlex.quote(value)

    @classmethod
    def _recovery(cls, directory: Path, console: Any) -> None:
        console.info("Your project files are intact. Resume environment setup without regenerating them:")
        console.info(f"  python -m flaxon new {cls._quote(str(directory))} --resume-venv --venv-timeout 300")
        console.info(
            "Environment setup uses Python's bundled pip; application dependencies are installed separately."
        )

    @classmethod
    def _next_steps(cls, directory: Path, console: Any, *, environment: bool, fullstack: bool) -> None:
        console.info("\nNext steps (install application dependencies separately):")
        command = "Set-Location -LiteralPath" if os.name == "nt" else "cd --"
        console.info(f"  {command} {cls._quote(str(directory))}")
        python = (
            (".\\.venv\\Scripts\\python.exe" if os.name == "nt" else ".venv/bin/python")
            if environment
            else "python"
        )
        if environment:
            console.info("Activation is optional; these commands use your project's Python directly.")
        console.info(f"  {python} -m pip install -e .")
        if fullstack:
            console.info(f"  {python} management.py check")
            console.info(f"  {python} -m flaxon welcome")
            console.info(f"  {python} management.py makemigrations")
            console.info(f"  {python} management.py migrate")
            console.info(f"  {python} management.py setup-admin")
            console.info(f"  {python} management.py runserver")
        else:
            console.info(f"  {python} -m flaxon run app:app --reload")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        directory = Path(args.directory)
        resume = getattr(args, "resume_venv", False)
        if directory.exists() and not resume:
            console.error(f"Directory '{args.directory}' already exists; no files were changed.")
            console.info("For a previously generated project, use --resume-venv to finish environment setup.")
            return 1
        if resume and not ((directory / "pyproject.toml").is_file() and (directory / "app.py").is_file()):
            console.error("--resume-venv requires an existing project with app.py and pyproject.toml.")
            return 1
        try:
            if not resume:
                console.info(f"Creating Flaxon project: {args.directory}")
                Generator().generate(directory, args.template)
            console.info(f"Project files ready at {directory.resolve()}")
            if not args.no_venv:
                self._create_environment(directory, console, timeout=getattr(args, "venv_timeout", 120.0))
            console.success(
                "Project setup complete."
                if not args.no_venv
                else "Project files created; environment setup skipped."
            )
            self._next_steps(
                directory,
                console,
                environment=not args.no_venv,
                fullstack=(directory / "management.py").is_file(),
            )
            return 0
        except subprocess.TimeoutExpired as exc:
            console.error(f"Environment setup timed out after {exc.timeout:g} seconds in this phase.")
            self._recovery(directory, console)
            return 1
        except KeyboardInterrupt:
            console.error("Setup cancelled; the environment setup process was stopped.")
            if directory.exists():
                self._recovery(directory, console)
            return 130
        except Exception as exc:
            console.error(f"Setup failed: {exc}")
            if (directory / "pyproject.toml").is_file():
                self._recovery(directory, console)
            return 1

    @staticmethod
    def _stop_process(process: Any) -> None:
        if process.poll() is not None:
            return
        pid = getattr(process, "pid", None)
        if pid is not None and os.name == "nt":
            subprocess.run(  # noqa: S603 - owned subprocess PID; no shell
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif pid is not None:
            with suppress(ProcessLookupError):
                os.killpg(pid, signal.SIGTERM)
        else:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if pid is not None and os.name != "nt":
                with suppress(ProcessLookupError):
                    os.killpg(pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait()

    @staticmethod
    def _run_step(command: list[str], directory: Path, console: Any, phase: str, timeout: float) -> None:
        console.info(f"{phase} (timeout: {timeout:g}s)...")
        process = subprocess.Popen(command, cwd=directory, start_new_session=os.name != "nt")  # noqa: S603 - local argument list; no shell
        started = time.monotonic()
        try:
            while True:
                elapsed = time.monotonic() - started
                remaining = timeout - elapsed
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                try:
                    code = process.wait(timeout=min(3, remaining))
                    if code:
                        raise subprocess.CalledProcessError(code, command)
                    console.info(f"{phase} finished in {time.monotonic() - started:.1f}s.")
                    return
                except subprocess.TimeoutExpired:
                    elapsed = time.monotonic() - started
                    if elapsed >= timeout:
                        raise subprocess.TimeoutExpired(command, timeout) from None
                    console.info(f"  {phase}: {elapsed:.0f}s elapsed; still working. Ctrl+C cancels safely.")
        finally:
            NewCommand._stop_process(process)

    @staticmethod
    def _create_environment(directory: Path, console: Any, *, timeout: float = 120.0) -> None:
        """Separate environment creation from offline bundled-pip installation."""
        if (directory / ".venv").is_symlink():
            raise ValueError(
                "Refusing to modify a .venv symlink; use your existing environment with --no-venv."
            )
        if Path(sys.prefix).resolve() == (directory / ".venv").resolve():
            console.info("Using the active project environment; checking bundled pip.")
        else:
            NewCommand._run_step(
                [sys.executable, "-u", "-m", "venv", "--without-pip", ".venv"],
                directory,
                console,
                "Creating virtual environment",
                timeout,
            )
        python = directory.resolve() / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        NewCommand._run_step(
            [str(python), "-u", "-m", "ensurepip", "--upgrade"],
            directory,
            console,
            "Installing bundled pip",
            timeout,
        )
