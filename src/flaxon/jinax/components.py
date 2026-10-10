from __future__ import annotations

from pathlib import Path
from typing import Any


class Component:
    """Component implementation for the jinax subsystem."""

    def __init__(self, name: str, template: str) -> None:
        self.name = name
        self.template = template
        self._slots: dict[str, str] = {}

    def render(self, context: dict[str, Any]) -> str:
        """Render the requested content using the supplied context."""
        return self.template.format(**context)

    def slot(self, name: str, content: str) -> None:
        """Perform the slot operation for component."""
        self._slots[name] = content


class ComponentRegistry:
    """Component registry implementation for the jinax subsystem."""

    def __init__(self) -> None:
        """Perform the   init   operation for component registry."""
        self._components: dict[str, Component] = {}

    def register(self, component: Component) -> None:
        """Perform the register operation for component registry."""
        self._components[component.name] = component

    def get(self, name: str) -> Component | None:
        """Retrieve the requested value using this object's configured behavior."""
        return self._components.get(name)

    def render(self, name: str, context: dict[str, Any]) -> str:
        """Render the requested content using the supplied context."""
        component = self.get(name)
        if component is None:
            return ""
        return component.render(context)

    def list_components(self) -> list[str]:
        """List the components."""
        return list(self._components.keys())


class ComponentLoader:
    """Component loader implementation for the jinax subsystem."""

    def __init__(self, directory: str) -> None:
        self.directory = directory
        self.registry = ComponentRegistry()

    def load_components(self) -> None:
        """Load the components."""
        path = Path(self.directory)
        if not path.exists():
            return

        for file in path.glob("*.html"):
            name = file.stem
            with Path(file).open(encoding="utf-8") as f:
                content = f.read()
            self.registry.register(Component(name, content))
