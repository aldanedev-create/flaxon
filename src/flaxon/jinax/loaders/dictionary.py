from __future__ import annotations

from collections.abc import Callable
from typing import Any


class DictionaryLoader:
    """Dictionary loader implementation for the jinax subsystem."""

    def __init__(self, mapping: dict[str, str] | None = None) -> None:
        self.mapping = mapping or {}

    def get_source(
        self, environment: Any, template: str
    ) -> tuple[str, str | None, Callable[[], bool] | None]:
        """Return the source."""
        if template not in self.mapping:
            raise FileNotFoundError(f"Template '{template}' not found in dictionary")

        source = self.mapping[template]

        def uptodate() -> bool:
            return True

        return source, f"dictionary:{template}", uptodate

    def list_templates(self) -> list[str]:
        """List the templates."""
        return list(self.mapping.keys())

    def exists(self, template: str) -> bool:
        """Return whether the requested entry exists."""
        return template in self.mapping

    def add_template(self, name: str, source: str) -> None:
        """Add the template."""
        self.mapping[name] = source

    def remove_template(self, name: str) -> None:
        """Remove the template."""
        self.mapping.pop(name, None)

    def clear(self) -> None:
        """Remove the stored entries."""
        self.mapping.clear()

    def update(self, mapping: dict[str, str]) -> None:
        """Apply the supplied changes to the requested entry."""
        self.mapping.update(mapping)
