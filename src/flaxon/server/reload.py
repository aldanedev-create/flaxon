from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


class Reloader:
    def __init__(self, watch_paths: list[str] | None = None, delay: float = 0.5) -> None:
        self.watch_paths = watch_paths or ["."]
        self.delay = delay
        self._mtimes: dict[str, float] = {}
        self._running = False
        self._process: subprocess.Popen | None = None

    def start_watching(self) -> None:
        self._running = True
        self._scan_files()

    def stop_watching(self) -> None:
        self._running = False

    def _scan_files(self) -> None:
        for path in self.watch_paths:
            self._scan_directory(Path(path))

    def _scan_directory(self, directory: Path) -> None:
        if not directory.exists():
            return

        for item in directory.rglob("*"):
            if item.is_file() and self._should_watch(item):
                self._check_file(item)

    def _should_watch(self, path: Path) -> bool:
        extensions = {".py", ".html", ".css", ".js", ".toml", ".yaml", ".yml", ".json"}
        skip_dirs = {".venv", "venv", "__pycache__", ".git", ".pytest_cache", ".mypy_cache","node_modules"}

        if any(part in skip_dirs for part in path.parts):
            return False

        return path.suffix in extensions

    def _check_file(self, path: Path) -> None:
        try:
            mtime = path.stat().st_mtime
            key = str(path)

            if key in self._mtimes:
                if self._mtimes[key] != mtime:
                    self._mtimes[key] = mtime
                    self._reload()
            else:
                self._mtimes[key] = mtime
        except OSError:
            pass

    def _reload(self) -> None:
        print("\n[Reloader] Detected changes, restarting...")

        if self._process:
            self._process.terminate()
            self._process.wait()

        self._start_process()

    def _start_process(self) -> None:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        self._process = subprocess.Popen(
            [sys.executable, "-m", "flaxon", "run"] + sys.argv[1:],
            env=env,
        )
