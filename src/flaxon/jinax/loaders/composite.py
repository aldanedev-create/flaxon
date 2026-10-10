from __future__ import annotations

from collections.abc import Callable
from typing import Any

try:
    from jinja2 import BaseLoader, TemplateNotFound
except ImportError:  # pragma: no cover - Jinax raises a clearer error when used.
    TemplateNotFound = FileNotFoundError

    class BaseLoader:  # type: ignore[no-redef]
        """Fallback base so importing optional loader helpers stays lightweight."""

        pass


class CompositeLoader(BaseLoader):
    """Composite loader implementation for the jinax subsystem."""

    def __init__(self, loaders: list[Any] | None = None) -> None:
        self.loaders = loaders or []

    def add_loader(self, loader: Any) -> None:
        """Add the loader."""
        self.loaders.append(loader)

    def remove_loader(self, loader: Any) -> None:
        """Remove the loader."""
        if loader in self.loaders:
            self.loaders.remove(loader)

    def get_source(
        self, environment: Any, template: str
    ) -> tuple[str, str | None, Callable[[], bool] | None]:
        """Return the source."""
        for loader in self.loaders:
            try:
                return loader.get_source(environment, template)
            except (FileNotFoundError, TemplateNotFound):
                continue

        raise FileNotFoundError(f"Template '{template}' not found in any loader")

    def list_templates(self) -> list[str]:
        """List the templates."""
        templates = set()
        for loader in self.loaders:
            if hasattr(loader, "list_templates"):
                templates.update(loader.list_templates())
        return list(templates)

    def exists(self, template: str) -> bool:
        """Return whether the requested entry exists."""
        return any(hasattr(loader, "exists") and loader.exists(template) for loader in self.loaders)

    def get_loader_for_template(self, template: str) -> Any | None:
        """Return the loader for template."""
        for loader in self.loaders:
            if hasattr(loader, "exists") and loader.exists(template):
                return loader
        return None

    def clear(self) -> None:
        """Remove the stored entries."""
        self.loaders.clear()

    def __len__(self) -> int:
        return len(self.loaders)

    def __iter__(self):
        return iter(self.loaders)
