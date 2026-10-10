"""Locate the request passed to a protected endpoint."""

from itertools import chain
from typing import Any

from flaxon.http import Request


def endpoint_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Request | None:
    """Find the first Request, preserving positional-before-keyword precedence."""
    return next((value for value in chain(args, kwargs.values()) if isinstance(value, Request)), None)
