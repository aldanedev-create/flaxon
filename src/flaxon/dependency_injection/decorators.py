from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from .container import Container

F = TypeVar("F", bound=Callable[..., Any])


def inject(container: Container | None = None) -> Callable[[F], F]:
    """Decorate a callable to inject registered annotated dependencies."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            sig = inspect.signature(func)
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()

            for name, param in sig.parameters.items():
                if name in kwargs:
                    continue

                if hasattr(param.annotation, "__name__"):
                    dep_name = param.annotation.__name__
                    if container and container.has(dep_name) and name not in kwargs:
                        kwargs[name] = container.get(dep_name)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def provide(container: Container | None = None) -> Callable[[F], F]:
    """Decorate a callable to register its result as a named instance."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if container:
                result = func(*args, **kwargs)
                container.register_instance(func.__name__, result)
                return result
            return func(*args, **kwargs)

        return wrapper

    return decorator


def autowire(container: Container) -> Callable[[F], F]:
    """Fill missing arguments using providers named for their annotated types."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            sig = inspect.signature(func)
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()

            for name, param in sig.parameters.items():
                if name not in kwargs and name not in bound_args.arguments:
                    annotation = param.annotation

                    if annotation is not inspect.Parameter.empty and hasattr(annotation, "__name__"):
                        dep_name = annotation.__name__
                        if container.has(dep_name):
                            kwargs[name] = container.get(dep_name)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def service(name: str | None = None, singleton: bool = True) -> Callable:
    """Wrap class construction; registration is still managed by the container."""

    def decorator(cls: type) -> type:
        original_init = cls.__init__

        def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
            if original_init is not object.__init__:
                original_init(self, *args, **kwargs)

        cls.__init__ = new_init

        return cls

    return decorator


def dependency(name: str | None = None) -> Callable:
    """Return a class marker decorator without registering the class."""

    def decorator(cls: type) -> type:
        return cls

    return decorator
