from __future__ import annotations

import inspect
import typing
from collections.abc import Callable
from typing import Any

from flaxon.routing.execution import EndpointPlan

from .exceptions import DependencyNotFoundError


def _resolved_hints(func: Callable[..., Any]) -> dict[str, Any]:
    """Best-effort resolution of string annotations (PEP 563) back to real types."""
    try:
        return typing.get_type_hints(func)
    except (NameError, TypeError, AttributeError):
        return {}


class Resolver:
    """Resolve current dependency providers for endpoint parameters."""

    def __init__(self, container: Any) -> None:
        self.container = container

    def resolve(self, func: Callable[..., Any]) -> dict[str, Any]:
        """Prepare endpoint metadata and resolve its current providers."""
        return self.resolve_plan(EndpointPlan.prepare(func))

    def resolve_plan(self, plan: EndpointPlan) -> dict[str, Any]:
        """Resolve current providers from precomputed endpoint metadata."""
        params = {}

        for name, type_name in plan.dependency_names:
            provider = self.container.get_provider(name)
            if provider is None and type_name is not None:
                provider = self.container.get_provider(type_name)
            if provider is not None:
                params[name] = provider[0].get(provider[1])

        return params

    def resolve_parameter(self, name: str, annotation: Any) -> Any:
        """Find a dependency by parameter name or annotated type."""
        if self.container.has(name):
            return self.container.get(name)

        if isinstance(annotation, type):
            try:
                return self.container.get(annotation.__name__)
            except DependencyNotFoundError:
                pass

        raise DependencyNotFoundError(f"Cannot resolve parameter '{name}'")

    def resolve_dependencies(self, dependencies: dict[str, Any]) -> dict[str, Any]:
        """Resolve explicit names and types, preserving literal values."""
        result = {}

        for name, dep in dependencies.items():
            if isinstance(dep, str):
                result[name] = self.container.get(dep)
            elif isinstance(dep, type):
                result[name] = self.container.get(dep.__name__)
            else:
                result[name] = dep

        return result

    def get_dependencies(self, func: Callable[..., Any]) -> dict[str, Any]:
        """Resolve registered parameters and retain unresolved defaults."""
        signature = inspect.signature(func)
        hints = _resolved_hints(func)
        deps = {}

        for name, param in signature.parameters.items():
            annotation = hints.get(name, param.annotation)

            if self.container.has(name):
                deps[name] = self.container.get(name)
            elif isinstance(annotation, type):
                try:
                    deps[name] = self.container.get(annotation.__name__)
                except DependencyNotFoundError:
                    deps[name] = param.default

        return deps
