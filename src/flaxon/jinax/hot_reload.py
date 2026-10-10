from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any


class HotReloader:
    """Hot reloader implementation for the jinax subsystem."""

    def __init__(self, template_dir: str | Path, check_interval: float = 1.0) -> None:
        self.template_dir = Path(template_dir)
        self.check_interval = check_interval
        self._mtime_cache: dict[str, float] = {}
        self._listeners: list[Callable[[str], None]] = []
        self._running = False
        self._task = None

    def watch(self) -> None:
        """Perform the watch operation for hot reloader."""
        self._running = True
        self._scan_templates()

    def stop(self) -> None:
        """Stop the configured service."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    def add_listener(self, listener: Callable[[str], None]) -> None:
        """Add the listener."""
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[str], None]) -> None:
        """Remove the listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _scan_templates(self) -> None:
        if not self.template_dir.exists():
            return

        for file_path in self.template_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in {".html", ".htm", ".xml"}:
                self._check_file(file_path)

    def _check_file(self, file_path: Path) -> None:
        try:
            mtime = file_path.stat().st_mtime
            key = str(file_path)

            if key in self._mtime_cache:
                if self._mtime_cache[key] != mtime:
                    self._mtime_cache[key] = mtime
                    self._notify_changed(key)
            else:
                self._mtime_cache[key] = mtime
        except OSError:
            pass

    def _notify_changed(self, path: str) -> None:
        for listener in self._listeners:
            try:
                listener(path)
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Isolated callback or cleanup failed (%s)", type(exc).__name__
                )

    async def run(self) -> None:
        """Run the configured operation."""
        self.watch()

        while self._running:
            self._scan_templates()
            await asyncio.sleep(self.check_interval)


class HotReloadMiddleware:
    """Hot reload middleware implementation for the jinax subsystem."""

    def __init__(self, app: Any, template_dir: str | Path, check_interval: float = 1.0) -> None:
        self.app = app
        self.reloader = HotReloader(template_dir, check_interval)
        self._reload_task = None

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        if self._reload_task is None:
            self._reload_task = asyncio.create_task(self.reloader.run())

        await self.app(scope, receive, send)


class TemplateWatcher:
    """Template watcher implementation for the jinax subsystem."""

    def __init__(self, template_dir: str | Path) -> None:
        self.template_dir = Path(template_dir)
        self._watched_files: dict[str, float] = {}

    def check_changes(self) -> list[str]:
        """Check the changes."""
        changed = []

        if not self.template_dir.exists():
            return changed

        for file_path in self.template_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in {".html", ".htm", ".xml"}:
                try:
                    mtime = file_path.stat().st_mtime
                    key = str(file_path)

                    if key in self._watched_files:
                        if self._watched_files[key] != mtime:
                            self._watched_files[key] = mtime
                            changed.append(key)
                    else:
                        self._watched_files[key] = mtime
                except OSError:
                    pass

        return changed

    def reset(self) -> None:
        """Perform the reset operation for template watcher."""
        self._watched_files.clear()

    def add_file(self, path: str) -> None:
        """Add the file."""
        try:
            mtime = Path(path).stat().st_mtime
            self._watched_files[path] = mtime
        except OSError:
            pass
