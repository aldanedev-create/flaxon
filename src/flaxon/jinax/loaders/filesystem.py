from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any


class FileSystemLoader:
    """File system loader implementation for the jinax subsystem."""

    def __init__(self, search_path: str | Path, encoding: str = "utf-8") -> None:
        self.search_path = Path(search_path)
        self.encoding = encoding
        self._cache: dict[str, tuple[str, float]] = {}

    def get_source(
        self, environment: Any, template: str
    ) -> tuple[str, str | None, Callable[[], bool] | None]:
        """Return the source."""
        path = self.search_path / template

        if not path.exists():
            raise FileNotFoundError(f"Template '{template}' not found in {self.search_path}")

        with Path(path).open(encoding=self.encoding) as f:
            source = f.read()

        mtime = path.stat().st_mtime

        def uptodate() -> bool:
            try:
                return path.stat().st_mtime == mtime
            except OSError:
                return False

        return source, str(path), uptodate

    def list_templates(self) -> list[str]:
        """List the templates."""
        if not self.search_path.exists():
            return []

        templates = []
        for path in self.search_path.rglob("*"):
            if path.is_file():
                rel_path = path.relative_to(self.search_path)
                templates.append(str(rel_path).replace(os.sep, "/"))

        return templates

    def exists(self, template: str) -> bool:
        """Return whether the requested entry exists."""
        return (self.search_path / template).exists()

    def get_mtime(self, template: str) -> float:
        """Return the mtime."""
        path = self.search_path / template
        if path.exists():
            return path.stat().st_mtime
        return 0
