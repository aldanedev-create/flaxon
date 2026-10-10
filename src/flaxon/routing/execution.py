"""Immutable endpoint metadata prepared outside the request path."""

from __future__ import annotations

import inspect
import types
import typing
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from flaxon.integrations.pydantic import prepare_response_adapter


@dataclass(frozen=True)
class EndpointPlan:
    """Parameters and resolved annotations; dependency values remain request-local."""

    parameters: tuple[tuple[str, inspect.Parameter, Any], ...]

    response_adapter: Any = None

    dependency_names: tuple[tuple[str, str | None], ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dependency_names",
            tuple(
                (name, annotation.__name__ if isinstance(annotation, type) else None)
                for name, _, annotation in self.parameters
            ),
        )

    @classmethod
    def prepare(cls, endpoint: Callable[..., Any]) -> EndpointPlan:
        """Inspect once, allowing unresolved forward references in local functions."""
        signature = inspect.signature(endpoint)
        try:
            hints = typing.get_type_hints(endpoint)
        except (NameError, TypeError, AttributeError):
            hints = {}
        return cls(
            tuple(
                (name, parameter, hints.get(name, parameter.annotation))
                for name, parameter in signature.parameters.items()
            ),
            prepare_response_adapter(hints.get("return", signature.return_annotation)),
        )


def is_scalar_query(annotation: Any) -> bool:
    """Infer only scalar and optional scalar query declarations."""
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        values = [value for value in typing.get_args(annotation) if value is not type(None)]
        return len(values) == 1 and values[0] in (str, int, float, bool)
    return annotation in (str, int, float, bool)
