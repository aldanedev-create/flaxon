from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flaxon._imports import import_attribute


class Environment:
    """Environment implementation for the jinax subsystem."""

    def __init__(
        self,
        loader: Any,
        autoescape: bool = True,
        enable_async: bool = True,
        auto_reload: bool = False,
        strict_undefined: bool = False,
    ) -> None:
        try:
            jinja_environment_type = import_attribute("jinja2", "Environment")
            strict_undefined_type = import_attribute("jinja2", "StrictUndefined")
            undefined_type = import_attribute("jinja2", "Undefined")
            select_autoescape = import_attribute("jinja2", "select_autoescape")
        except ImportError as exc:
            raise RuntimeError("Jinja2 is required. Install with: pip install jinja2") from exc

        undefined = strict_undefined_type if strict_undefined else undefined_type
        self._env = jinja_environment_type(
            loader=loader,
            autoescape=select_autoescape(("html", "htm", "xml")) if autoescape else False,
            enable_async=enable_async,
            auto_reload=auto_reload,
            undefined=undefined,
        )
        self._globals: dict[str, Any] = {}
        self._filters: dict[str, Callable[..., Any]] = {}

    def add_global(self, name: str, value: Any) -> None:
        """Add the global."""
        self._globals[name] = value
        self._env.globals[name] = value

    def add_filter(self, name: str, func: Callable[..., Any]) -> None:
        """Add the filter."""
        self._filters[name] = func
        self._env.filters[name] = func

    def get_template(self, name: str) -> Any:
        """Return the template."""
        return self._env.get_template(name)

    def from_string(self, source: str) -> Any:
        """Construct from the string."""
        return self._env.from_string(source)

    @property
    def globals(self) -> dict[str, Any]:
        """Return the configured globals."""
        return self._globals

    @property
    def filters(self) -> dict[str, Callable[..., Any]]:
        """Return the configured filters."""
        return self._filters
