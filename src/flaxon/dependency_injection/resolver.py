from __future__ import annotations

import inspect
import typing
from collections.abc import Callable
from typing import Any

from flaxon.routing.execution import EndpointPlan

from .exceptions import DependencyNotFoundError


def _resolved_hints(func: Callable) -> dict[str, Any]:
    """Best-effort resolution of string annotations (PEP 563) back to real types."""
    try:
        return typing.get_type_hints(func)
    except Exception:
        return {}


class Resolver:
    def __init__(self, container: Any) -> None:
        self.container = container

    def resolve(self, func: Callable) -> dict[str, Any]:
        return self.resolve_plan(EndpointPlan.prepare(func))

    def resolve_plan(self, plan: EndpointPlan) -> dict[str, Any]:
        """Resolve current providers from precomputed endpoint metadata."""
        params = {}

        for name, param, annotation in plan.parameters:
            if self.container.has(name):
                params[name] = self.container.get(name)
            elif isinstance(annotation, type):
                try:
                    params[name] = self.container.get(annotation.__name__)
                except DependencyNotFoundError:
                    pass

        return params

    def resolve_parameter(self, name: str, annotation: Any) -> Any:
        if self.container.has(name):
            return self.container.get(name)

        if isinstance(annotation, type):
            try:
                return self.container.get(annotation.__name__)
            except DependencyNotFoundError:
                pass

        raise DependencyNotFoundError(f"Cannot resolve parameter '{name}'")

    def resolve_dependencies(self, dependencies: dict[str, Any]) -> dict[str, Any]:
        result = {}

        for name, dep in dependencies.items():
            if isinstance(dep, str):
                result[name] = self.container.get(dep)
            elif isinstance(dep, type):
                result[name] = self.container.get(dep.__name__)
            else:
                result[name] = dep

        return result

    def get_dependencies(self, func: Callable) -> dict[str, Any]:
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