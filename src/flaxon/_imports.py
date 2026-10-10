"""Resolve optional integration exports when their feature is requested."""

from importlib import import_module
from types import ModuleType
from typing import Any


def import_attribute(module_name: str, name: str) -> Any:
    """Load a module export or child module using Python's from-import semantics.

    Call sites defer optional dependencies and circular framework integrations
    until the feature is used. Missing exports raise ImportError so existing
    optional-dependency fallbacks continue to work.
    """
    module: ModuleType = import_module(module_name)
    try:
        return getattr(module, name)
    except AttributeError as error:
        try:
            return import_module(f"{module_name}.{name}")
        except ModuleNotFoundError as missing:
            if missing.name != f"{module_name}.{name}":
                raise
            raise ImportError(f"cannot import name {name!r} from {module_name!r}") from error
