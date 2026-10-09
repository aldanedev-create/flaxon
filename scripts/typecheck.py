"""Run the checked core, or report the remaining whole-package typing debt."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKED_MODULES = (
    "routing/converters.py",
    "routing/execution.py",
    "routing/parameters.py",
    "routing/route.py",
    "routing/router.py",
    "dependency_injection/resolver.py",
    "tasks/signals.py",
    "tasks/worker.py",
    "http/body.py",
    "http/serialization.py",
    "security/jwt.py",
)


def main() -> int:
    """Check core contracts without suppressing errors in those modules."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Audit all modules; known debt currently fails.")
    args = parser.parse_args()
    command = [sys.executable, "-m", "mypy", "--config-file", "mypy.ini", "--no-incremental"]
    if args.full:
        command.append("src/flaxon")
    else:
        # Third-party and unchecked legacy implementations are not followed;
        # every module listed above is still checked with the strict config.
        command.extend(["--follow-imports=skip", *(f"src/flaxon/{name}" for name in CHECKED_MODULES)])
    # All arguments come from the fixed module list or the --full boolean.
    return subprocess.run(command, cwd=ROOT, check=False).returncode  # noqa: S603


if __name__ == "__main__":
    raise SystemExit(main())
