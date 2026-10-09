from __future__ import annotations

from collections.abc import Callable
from typing import Any


class DictionaryLoader:
    def __init__(self, mapping: dict[str, str] | None = None) -> None:
        self.mapping = mapping or {}

    def get_source(
        self, environment: Any, template: str
    ) -> tuple[str, str | None, Callable[[], bool] | None]:
        if template not in self.mapping:
            raise FileNotFoundError(f"Template '{template}' not found in dictionary")

        source = self.mapping[template]

        def uptodate() -> bool:
            return True

        return source, f"dictionary:{template}", uptodate

    def list_templates(self) -> list[str]:
        return list(self.mapping.keys())

    def exists(self, template: str) -> bool:
        return template in self.mapping

    def add_template(self, name: str, source: str) -> None:
        self.mapping[name] = source

    def remove_template(self, name: str) -> None:
        self.mapping.pop(name, None)

    def clear(self) -> None:
        self.mapping.clear()

    def update(self, mapping: dict[str, str]) -> None:
        self.mapping.update(mapping)
