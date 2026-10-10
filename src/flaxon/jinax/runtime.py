from __future__ import annotations

from typing import Any


class Runtime:
    """Runtime implementation for the jinax subsystem."""

    def __init__(self, environment: Any) -> None:
        self.environment = environment
        self._context: dict[str, Any] = {}

    def render(self, template: str, context: dict[str, Any] | None = None) -> str:
        """Render the requested content using the supplied context."""
        ctx = {**self._context, **(context or {})}
        template_obj = self.environment.get_template(template)
        return template_obj.render(**ctx)

    async def render_async(self, template: str, context: dict[str, Any] | None = None) -> str:
        """Render the async."""
        ctx = {**self._context, **(context or {})}
        template_obj = self.environment.get_template(template)
        return await template_obj.render_async(**ctx)

    def render_string(self, source: str, context: dict[str, Any] | None = None) -> str:
        """Render the string."""
        ctx = {**self._context, **(context or {})}
        template_obj = self.environment.from_string(source)
        return template_obj.render(**ctx)

    async def render_string_async(self, source: str, context: dict[str, Any] | None = None) -> str:
        """Render the string async."""
        ctx = {**self._context, **(context or {})}
        template_obj = self.environment.from_string(source)
        return await template_obj.render_async(**ctx)

    def add_global(self, name: str, value: Any) -> None:
        """Add the global."""
        self._context[name] = value

    def get_global(self, name: str) -> Any:
        """Return the global."""
        return self._context.get(name)

    def clear(self) -> None:
        """Remove the stored entries."""
        self._context.clear()
