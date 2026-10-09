from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from .exceptions import DependencyNotFoundError
from .provider import FactoryProvider, InstanceProvider, Provider, SingletonProvider
from .resolver import Resolver
from .scope import Scope

T = TypeVar("T")


class Container:
    def __init__(self, parent: Container | None = None) -> None:
        self.parent = parent
        self._providers: dict[str, Provider] = {}
        self._resolver = Resolver(self)
        self._scope = Scope()

    def register(self, name: str, provider: Provider) -> None:
        self._providers[name] = provider

    def register_instance(self, name: str, instance: Any) -> None:
        self._providers[name] = InstanceProvider(instance)

    def register_factory(self, name: str, factory: Callable[..., Any], singleton: bool = False) -> None:
        if singleton:
            self._providers[name] = SingletonProvider(factory)
        else:
            self._providers[name] = FactoryProvider(factory)

    def register_type(self, name: str, type_: type[T]) -> None:
        self._providers[name] = SingletonProvider(lambda: type_())

    def get(self, name: str) -> Any:
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
        try:
            return self.get(name)
        except DependencyNotFoundError:
            return default

    def has(self, name: str) -> bool:
        if name in self._providers:
            return True
        if self.parent is not None:
            return self.parent.has(name)
        return False

    def remove(self, name: str) -> None:
        self._providers.pop(name, None)

    def clear(self) -> None:
        self._providers.clear()

    def resolve(self, func: Callable) -> dict[str, Any]:
        return self._resolver.resolve(func)

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        params = self._resolver.resolve(func)
        params.update(kwargs)
        return func(*args, **params)

    async def call_async(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        params = self._resolver.resolve(func)
        params.update(kwargs)
        result = func(*args, **params)
        if hasattr(result, "__await__"):
            return await result
        return result

    def create_child(self) -> Container:
        return Container(parent=self)

    def enter_scope(self, scope_type: str = "request") -> Container:
        return self.create_child()

    def exit_scope(self) -> None:
        self.clear()

    def __contains__(self, name: str) -> bool:
        return self.has(name)

    def __getitem__(self, name: str) -> Any:
        return self.get(name)

    def __setitem__(self, name: str, value: Any) -> None:
        self.register_instance(name, value)
