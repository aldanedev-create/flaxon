from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any


class HotReloader:
    def __init__(self, template_dir: str | Path, check_interval: float = 1.0) -> None:
        self.template_dir = Path(template_dir)
        self.check_interval = check_interval
        self._mtime_cache: dict[str, float] = {}
        self._listeners: list[Callable[[str], None]] = []
        self._running = False
        self._task = None

    def watch(self) -> None:
        self._running = True
        self._scan_templates()

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    def add_listener(self, listener: Callable[[str], None]) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[str], None]) -> None:
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
                logging.getLogger(__name__).warning("Isolated callback or cleanup failed (%s)", type(exc).__name__)

    async def run(self) -> None:
        import asyncio

        self.watch()

        while self._running:
            self._scan_templates()
            await asyncio.sleep(self.check_interval)


class HotReloadMiddleware:
    def __init__(self, app: Any, template_dir: str | Path, check_interval: float = 1.0) -> None:
        self.app = app
        self.reloader = HotReloader(template_dir, check_interval)
        self._reload_task = None

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        if self._reload_task is None:
            import asyncio
            self._reload_task = asyncio.create_task(self.reloader.run())

        await self.app(scope, receive, send)


class TemplateWatcher:
    def __init__(self, template_dir: str | Path) -> None:
        self.template_dir = Path(template_dir)
        self._watched_files: dict[str, float] = {}

    def check_changes(self) -> list[str]:
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
        self._watched_files.clear()

    def add_file(self, path: str) -> None:
        try:
            mtime = os.path.getmtime(path)
            self._watched_files[path] = mtime
        except OSError:
            pass
