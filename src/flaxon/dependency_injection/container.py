from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from .exceptions import DependencyNotFoundError
from .provider import FactoryProvider, InstanceProvider, Provider, SingletonProvider
from .resolver import Resolver
from .scope import Scope

T = TypeVar("T")


class Container:
    """Register dependency providers and resolve them through a parent hierarchy."""

    def __init__(self, parent: Container | None = None) -> None:
        self.parent = parent
        self._providers: dict[str, Provider] = {}
        self._resolver = Resolver(self)
        self._scope = Scope()

    def register(self, name: str, provider: Provider) -> None:
        """Register a provider under a dependency name."""
        self._providers[name] = provider

    def register_instance(self, name: str, instance: Any) -> None:
        """Register an existing object as a dependency."""
        self._providers[name] = InstanceProvider(instance)

    def register_factory(self, name: str, factory: Callable[..., Any], singleton: bool = False) -> None:
        """Register a factory, optionally caching its result as a singleton."""
        if singleton:
            self._providers[name] = SingletonProvider(factory)
        else:
            self._providers[name] = FactoryProvider(factory)

    def register_type(self, name: str, type_: type[T]) -> None:
        """Register a type whose instance is created lazily without arguments."""
        self._providers[name] = SingletonProvider(lambda: type_())

    def get(self, name: str) -> Any:
        """Resolve a dependency, searching the parent container when necessary."""
        provider = self._providers.get(name)
        if provider is not None:
            return provider.get(self)

        if self.parent is not None:
            return self.parent.get(name)

        raise DependencyNotFoundError(f"Dependency '{name}' not found")

    def get_provider(self, name: str) -> tuple[Provider, Container] | None:
        """Find a current provider once, including parent registrations."""
        provider = self._providers.get(name)
        if provider is None and self.parent is not None:
            return self.parent.get_provider(name)
        return (provider, self) if provider is not None else None

    def get_optional(self, name: str, default: Any = None) -> Any:
        """Resolve a dependency or return the fallback if it is not registered."""
        try:
            return self.get(name)
        except DependencyNotFoundError:
            return default

    def has(self, name: str) -> bool:
        """Check whether this container or its parent provides a dependency."""
        if name in self._providers:
            return True
        if self.parent is not None:
            return self.parent.has(name)
        return False

    def remove(self, name: str) -> None:
        """Remove a provider registered directly in this container."""
        self._providers.pop(name, None)

    def clear(self) -> None:
        """Remove providers or local instances owned by this container."""
        self._providers.clear()

    def resolve(self, func: Callable) -> dict[str, Any]:
        """Resolve registered dependencies for a callable's parameters."""
        return self._resolver.resolve(func)

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Call a function with resolved dependencies and explicit keyword overrides."""
        params = self._resolver.resolve(func)
        params.update(kwargs)
        return func(*args, **params)

    async def call_async(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Call a function with resolved dependencies and await an awaitable result."""
        params = self._resolver.resolve(func)
        params.update(kwargs)
        result = func(*args, **params)
        if hasattr(result, "__await__"):
            return await result
        return result

    def create_child(self) -> Container:
        """Create a container that falls back to this container for dependencies."""
        return Container(parent=self)

    def enter_scope(self, scope_type: str = "request") -> Container:
        """Create a child container for scoped dependency registrations."""
        return self.create_child()

    def exit_scope(self) -> None:
        """Clear this container's directly registered dependencies."""
        self.clear()

    def __contains__(self, name: str) -> bool:
        return self.has(name)

    def __getitem__(self, name: str) -> Any:
        return self.get(name)

    def __setitem__(self, name: str, value: Any) -> None:
        self.register_instance(name, value)
