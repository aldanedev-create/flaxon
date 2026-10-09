from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any


class Loader:
    def __init__(self, search_path: str | Path, encoding: str = "utf-8") -> None:
        self.search_path = Path(search_path)
        self.encoding = encoding

    def get_source(
        self, environment: Any, template: str
    ) -> tuple[str, str | None, Callable[[], bool] | None]:
        path = self.search_path / template
        if not path.exists():
            raise TemplateNotFound(template)

        with open(path, encoding=self.encoding) as f:
            source = f.read()

        def uptodate() -> bool:
            return False

        return source, str(path), uptodate

    def list_templates(self) -> list[str]:
        if not self.search_path.exists():
            return []
        return [str(p.relative_to(self.search_path)) for p in self.search_path.rglob("*") if p.is_file()]


class TemplateNotFound(Exception):
    def __init__(self, template: str) -> None:
        super().__init__(f"Template '{template}' not found")
        self.template = template
