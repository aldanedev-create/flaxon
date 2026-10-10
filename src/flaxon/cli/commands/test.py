from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Any

from flaxon.cli.base import Command


class TestCommand(Command):
    """Test command implementation for the cli subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="test",
            handler=self._run,
            help_text="Run tests",
            description="Run the test suite using pytest",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
        parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
        parser.add_argument("--keep-env", action="store_true", help="Keep test environment")
        parser.add_argument("tests", nargs="*", help="Specific tests to run")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        cmd = ["pytest"]

        if args.verbose:
            cmd.append("-v")

        if args.coverage:
            cmd.extend(["--cov=flaxon", "--cov-report=term-missing"])

        if args.tests:
            cmd.extend(args.tests)

        console.info(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=False)  # noqa: S603 - local CLI argument list; no shell interpolation
            returncode = result.returncode
        except FileNotFoundError:
            console.error("pytest is not installed. Run: pip install pytest")
            return 1
        except KeyboardInterrupt:
            console.info("\nTests interrupted")
            return 1

        if not args.keep_env:
            self._cleanup_test_artifacts(console)

        return returncode

    def _cleanup_test_artifacts(self, console: Any) -> None:

        removed = []
        for name in (".pytest_cache", ".coverage", "htmlcov"):
            target = Path(name)
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    target.unlink(missing_ok=True)
                removed.append(name)

        if removed:
            console.info(f"Cleaned up test artifacts: {', '.join(removed)} (use --keep-env to preserve)")
