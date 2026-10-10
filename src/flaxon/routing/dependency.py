"""
Dependency injection for route parameters.

This module provides dependency injection functionality for resolving
route parameters and dependencies.
"""

from __future__ import annotations

import contextlib
import inspect
from collections.abc import Callable
from typing import Any, TypeVar

from flaxon.exceptions import DependencyError

T = TypeVar("T")


class Dependency:
    """
    Represents a dependency that can be injected into a route.

    Attributes:
        name: The dependency name.
        type: The dependency type.
        provider: The provider function.
        singleton: Whether the dependency is a singleton.
    """

    def __init__(
        self,
        name: str,
        type: type | None = None,
        provider: Callable[..., Any] | None = None,
        singleton: bool = False,
    ) -> None:
        """
        Initialize the dependency.

        Args:
            name: The dependency name.
            type: The dependency type.
            provider: The provider function.
            singleton: Whether the dependency is a singleton.
        """
        self.name = name
        self.type = type
        self.provider = provider or self._default_provider
        self.singleton = singleton
        self._instance: Any = None

    def _default_provider(self) -> Any:
        """Default provider that raises an error."""
        raise DependencyError(f"Dependency '{self.name}' has no provider")

    def resolve(self) -> Any:
        """
        Resolve the dependency.

        Returns:
            The resolved dependency instance.

        Raises:
            DependencyError: If the dependency cannot be resolved.
        """
        if self.singleton and self._instance is not None:
            return self._instance

        try:
            result = self.provider()
        except Exception as exc:
            raise DependencyError(f"Failed to resolve dependency '{self.name}': {exc}") from exc

        if self.singleton:
            self._instance = result

        return result


class DependencyContainer:
    """
    Container for managing dependencies.

    This class manages dependency registration and resolution.

    Example:
        ```python
        container = DependencyContainer()


        def get_db():
            return create_db_pool()


        container.register("db", provider=get_db, singleton=True)

        db = container.resolve("db")
        ```
    """

    def __init__(self) -> None:
        """Initialize the dependency container."""
        self._dependencies: dict[str, Dependency] = {}
        self._instances: dict[str, Any] = {}

    def register(
        self,
        name: str,
        *,
        type: type | None = None,
        provider: Callable[..., Any] | None = None,
        singleton: bool = False,
    ) -> None:
        """
        Register a dependency.

        Args:
            name: The dependency name.
            type: The dependency type.
            provider: The provider function.
            singleton: Whether the dependency is a singleton.

        Example:
            ```python
            container.register("db", provider=get_db_pool, singleton=True)
            ```
        """
        self._dependencies[name] = Dependency(name, type, provider, singleton)

    def register_instance(self, name: str, instance: Any, *, type: type | None = None) -> None:
        """
        Register a pre-created instance.

        Args:
            name: The dependency name.
            instance: The instance to register.
            type: The dependency type.
        """

        def provider() -> Any:
            return instance

        self.register(name, type=type, provider=provider, singleton=True)

    def resolve(self, name: str) -> Any:
        """
        Resolve a dependency by name.

        Args:
            name: The dependency name.

        Returns:
            The resolved dependency instance.

        Raises:
            DependencyError: If the dependency is not found or cannot be resolved.
        """
        if name in self._instances:
            return self._instances[name]

        if name not in self._dependencies:
            raise DependencyError(f"Dependency '{name}' not found")

        dep = self._dependencies[name]
        result = dep.resolve()

        if dep.singleton:
            self._instances[name] = result

        return result

    def resolve_type(self, type_: type[T]) -> T:
        """
        Resolve a dependency by type.

        Args:
            type_: The dependency type.

        Returns:
            The resolved dependency instance.

        Raises:
            DependencyError: If the dependency is not found or cannot be resolved.
        """
        for name, dep in self._dependencies.items():
            if dep.type and issubclass(dep.type, type_):
                return self.resolve(name)

        raise DependencyError(f"Dependency of type '{getattr(type_, '__name__', str(type_))}' not found")

    def has(self, name: str) -> bool:
        """
        Check if a dependency is registered.

        Args:
            name: The dependency name.

        Returns:
            True if the dependency is registered.
        """
        return name in self._dependencies

    def remove(self, name: str) -> None:
        """
        Remove a dependency.

        Args:
            name: The dependency name.
        """
        self._dependencies.pop(name, None)
        self._instances.pop(name, None)

    def clear(self) -> None:
        """Clear all dependencies."""
        self._dependencies.clear()
        self._instances.clear()

    def keys(self) -> list[str]:
        """Get all dependency names."""
        return list(self._dependencies.keys())

    def __contains__(self, name: str) -> bool:
        """Check if a dependency is registered."""
        return self.has(name)

    def __getitem__(self, name: str) -> Any:
        """Get a dependency by name."""
        return self.resolve(name)

    def __len__(self) -> int:
        """Get the number of registered dependencies."""
        return len(self._dependencies)


def inject_dependencies(
    func: Callable,
    container: DependencyContainer,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Inject dependencies into a function call.

    Args:
        func: The function to inject dependencies into.
        container: The dependency container.
        extra_params: Extra parameters to pass.

    Returns:
        A dictionary of resolved parameters.

    Example:
        ```python
        def handler(db, request):
            return db.query(request.path)


        params = inject_dependencies(handler, container, {"request": request})
        result = handler(**params)
        ```
    """
    signature = inspect.signature(func)
    params: dict[str, Any] = {}
    extra_params = extra_params or {}

    for name, param in signature.parameters.items():
        if name in extra_params:
            params[name] = extra_params[name]
            continue

        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            if container.has(name):
                params[name] = container.resolve(name)
            continue

        if container.has(name):
            params[name] = container.resolve(name)
        elif annotation is not inspect.Parameter.empty:
            with contextlib.suppress(DependencyError):
                params[name] = container.resolve_type(annotation)

    return params


def with_dependencies(container: DependencyContainer) -> Callable:
    """
    Decorator to inject dependencies into a route.

    Args:
        container: The dependency container.

    Returns:
        A decorator function.

    Example:
        ```python
        @app.get("/users")
        @with_dependencies(container)
        async def get_users(db):
            return await db.query("SELECT * FROM users")
        ```
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            params = inject_dependencies(func, container, kwargs)
            if inspect.iscoroutinefunction(func):
                return await func(*args, **params)
            return func(*args, **params)

        return wrapper

    return decorator
