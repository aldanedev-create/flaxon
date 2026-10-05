from __future__ import annotations

from collections.abc import Callable
from typing import Any

try:
    from jinja2 import BaseLoader
except ImportError:  # pragma: no cover - Jinax raises a clearer error when used.
    class BaseLoader:  # type: ignore[no-redef]
        """Fallback base so importing optional loader helpers stays lightweight."""

        pass


class CompositeLoader(BaseLoader):
    def __init__(self, loaders: list[Any] | None = None) -> None:
        self.loaders = loaders or []

    def add_loader(self, loader: Any) -> None:
        self.loaders.append(loader)

    def remove_loader(self, loader: Any) -> None:
        if loader in self.loaders:
            self.loaders.remove(loader)

    def get_source(self, environment: Any, template: str) -> tuple[str, str | None, Callable[[], bool] | None]:
        for loader in self.loaders:
            try:
                return loader.get_source(environment, template)
            except FileNotFoundError:
                continue

        raise FileNotFoundError(f"Template '{template}' not found in any loader")

    def list_templates(self) -> list[str]:
        templates = set()
        for loader in self.loaders:
            if hasattr(loader, "list_templates"):
                templates.update(loader.list_templates())
        return list(templates)

    def exists(self, template: str) -> bool:
        for loader in self.loaders:
            if hasattr(loader, "exists"):
                if loader.exists(template):
                    return True
        return False

    def get_loader_for_template(self, template: str) -> Any | None:
        for loader in self.loaders:
            if hasattr(loader, "exists"):
                if loader.exists(template):
                    return loader
        return None

    def clear(self) -> None:
        self.loaders.clear()

    def __len__(self) -> int:
        return len(self.loaders)

    def __iter__(self):
        return iter(self.loaders)
