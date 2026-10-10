from __future__ import annotations

import functools
import warnings
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def deprecated(
    message: str | None = None,
    version: str | None = None,
    removal_version: str | None = None,
) -> Callable[[T], T]:
    """Mark a function as deprecated."""

    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            msg = message or f"{func.__name__} is deprecated"
            if version:
                msg += f" since version {version}"
            if removal_version:
                msg += f" and will be removed in version {removal_version}"
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def deprecated_parameter(
    param_name: str,
    message: str | None = None,
    version: str | None = None,
    removal_version: str | None = None,
) -> Callable[[T], T]:
    """Mark a function parameter as deprecated."""

    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if param_name in kwargs:
                msg = message or f"Parameter '{param_name}' is deprecated"
                if version:
                    msg += f" since version {version}"
                if removal_version:
                    msg += f" and will be removed in version {removal_version}"
                warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def warn_deprecated(message: str, stacklevel: int = 2) -> None:
    """Issue a deprecation warning."""
    warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)


class DeprecatedMeta(type):
    """Metaclass that warns when a deprecated class is instantiated."""

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Handle the supplied call using this object's configured behavior."""
        warnings.warn(
            f"{cls.__name__} is deprecated",
            DeprecationWarning,
            stacklevel=2,
        )
        return super().__call__(*args, **kwargs)
