from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from .registry import default_registry


def admin_model(**options: Any) -> Callable[[type], type]:
    """Decorator to register a model class with the default admin registry."""
    def decorator(cls: type) -> type:
        default_registry.register(cls, **options)
        return cls
    return decorator


def admin_action(name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to mark a function or method as an admin bulk action."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        wrapper._admin_action = name or func.__name__
        return wrapper
    return decorator


def admin_display(header: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to mark a method as a custom column display in admin views."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        wrapper._admin_display = True
        wrapper._admin_header = header or func.__name__.replace("_", " ").title()
        return wrapper
    return decorator
