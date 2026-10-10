from __future__ import annotations

import argparse
import secrets
from pathlib import Path
from typing import Any

from flaxon._imports import import_attribute
from flaxon.cli.base import Command


class DoctorCommand(Command):
    """Doctor command implementation for the cli subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="doctor",
            handler=self._run,
            help_text="Check application configuration and routes",
            description="Run diagnostics on the application",
        )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("application", help="Application import string, e.g., app:app")
        parser.add_argument("--fix", action="store_true", help="Attempt to fix issues")

    def _run(self, args: argparse.Namespace, console: Any) -> int:
        import_string = import_attribute("flaxon.utils.import_string", "import_string")

        try:
            app = import_string(args.application)
        except Exception as exc:
            console.error(f"Failed to import application: {exc}")
            return 1

        warnings = []
        failures = []
        weak_secret_key = False

        console.info(f"Flaxon Doctor - {app.name}")

        console.success("[PASS] Application imported successfully")
        console.success(f"[PASS] {len(app.router.routes)} HTTP route(s) registered")
        console.success(f"[PASS] {len(app.router.websocket_routes)} WebSocket route(s) registered")

        if app.debug and str(app.config.get("ENV", "development")).lower() == "production":
            warnings.append("Debug mode is enabled in production.")

        if app.config.get("SECRET_KEY") in {None, "", "change-me", "change-this-in-production"}:
            warnings.append("A strong production SECRET_KEY is not configured.")
            weak_secret_key = True

        seen = set()
        for route in app.router.routes:
            key = (route.path, tuple(sorted(route.methods)))
            if key in seen:
                failures.append(f"Duplicate route: {route.methods} {route.path}")
            seen.add(key)

        for warning in warnings:
            console.warning(f"[WARN] {warning}")

        for failure in failures:
            console.error(f"[FAIL] {failure}")

        console.info(f"Result: {len(warnings)} warning(s), {len(failures)} failure(s)")

        if args.fix:
            self._run_fix(
                console=console, failures=failures, warnings=warnings, weak_secret_key=weak_secret_key
            )

        return 1 if failures else 0

    def _run_fix(self, *, console, failures, warnings, weak_secret_key):
        """Apply fix changes for run."""
        if weak_secret_key:
            self._fix_secret_key(console)
        elif not (warnings or failures):
            console.info("Nothing to fix.")

        if failures:
            console.warning(
                "Duplicate routes can't be fixed automatically -- "
                "edit your route definitions to remove the conflict."
            )

    def _fix_secret_key(self, console: Any) -> None:

        env_path = Path(".env")
        existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""

        if any(line.strip().startswith("SECRET_KEY=") for line in existing.splitlines()):
            console.info(".env already defines SECRET_KEY -- leaving it as is.")
            return

        new_key = secrets.token_urlsafe(48)
        with env_path.open("a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write(f"SECRET_KEY={new_key}\n")

        console.success(f"Generated a SECRET_KEY and wrote it to {env_path}")
        console.info("Load it with: flaxon run app:app --env-file .env")
