from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from flaxon._imports import import_attribute
from flaxon.http import HTMLResponse


class Jinax:
    """Jinax implementation for the jinax subsystem."""

    def __init__(
        self,
        template_directory: str | Path = "templates",
        *,
        template_dir: str | Path | None = None,
        auto_reload: bool = False,
        strict_undefined: bool = True,
        globals: dict[str, Any] | None = None,
        filters: dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        try:
            environment_type = import_attribute("jinja2", "Environment")
            file_system_loader_type = import_attribute("jinja2", "FileSystemLoader")
            strict_undefined_type = import_attribute("jinja2", "StrictUndefined")
            undefined_type = import_attribute("jinja2", "Undefined")
            select_autoescape = import_attribute("jinja2", "select_autoescape")
        except ImportError as exc:
            raise RuntimeError(
                "Jinax requires Jinja2. Install it with: pip install 'flaxon-framework[templates]'"
            ) from exc

        if template_dir is not None:
            if template_directory != "templates":
                raise ValueError("Pass either template_directory or template_dir, not both")
            template_directory = template_dir

        undefined = strict_undefined_type if strict_undefined else undefined_type
        self.environment = environment_type(
            loader=file_system_loader_type(str(template_directory)),
            autoescape=select_autoescape(("html", "htm", "xml")),
            enable_async=True,
            auto_reload=auto_reload,
            undefined=undefined,
        )
        self.environment.globals.update({"now": datetime.now, **(globals or {})})
        self.environment.filters.update(filters or {})
        self.environment.filters.setdefault("currency", self.currency)

    @staticmethod
    def currency(value: Any, code: str = "USD") -> str:
        """Perform the currency operation for jinax."""
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return str(value)
        return f"{code} {amount:,.2f}"

    def add_global(self, name: str, value: Any) -> None:
        """Add the global."""
        self.environment.globals[name] = value

    def add_filter(self, name: str, func: Callable[..., Any]) -> None:
        """Add the filter."""
        self.environment.filters[name] = func

    async def render(self, template_name: str, context: dict[str, Any] | None = None) -> str:
        """Render the requested content using the supplied context."""
        template = self.environment.get_template(template_name)
        return await template.render_async(**(context or {}))

    async def render_response(
        self,
        template_name: str,
        context: dict[str, Any] | None = None,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> HTMLResponse:
        """Render the response."""
        html = await self.render(template_name, context)
        return HTMLResponse(html, status_code=status_code, headers=headers)
