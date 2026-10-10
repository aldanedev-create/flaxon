from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from flaxon._imports import import_attribute


class Provider(ABC):
    """The interface for obtaining a dependency from a container."""

    @abstractmethod
    def get(self, container: Any) -> Any:
        """Obtain a dependency value from the supplied container."""
        pass


class InstanceProvider(Provider):
    """Return an already constructed dependency instance."""

    def __init__(self, instance: Any) -> None:
        self.instance = instance

    def get(self, container: Any) -> Any:
        """Return the existing instance without constructing a new object."""
        return self.instance


class FactoryProvider(Provider):
    """Construct a dependency on each resolution."""

    def __init__(self, factory: Callable[..., Any]) -> None:
        self.factory = factory

    def get(self, container: Any) -> Any:
        """Call the registered factory to produce a new dependency value."""
        return self.factory()


class SingletonProvider(Provider):
    """Lazily construct and reuse one dependency instance."""

    def __init__(self, factory: Callable[..., Any]) -> None:
        self.factory = factory
        self._instance = None

    def get(self, container: Any) -> Any:
        """Return the cached instance, creating it on the first call."""
        if self._instance is None:
            self._instance = self.factory()
        return self._instance


class CallableProvider(Provider):
    """Provide a callable itself without invoking it."""

    def __init__(self, callable_obj: Callable) -> None:
        self.callable_obj = callable_obj

    def get(self, container: Any) -> Any:
        """Return the registered callable without executing it."""
        return self.callable_obj


class LazyProvider(Provider):
    """Import and cache a dependency on its first resolution."""

    def __init__(self, import_path: str) -> None:
        self.import_path = import_path
        self._instance = None

    def get(self, container: Any) -> Any:
        """Import the configured object once and return the cached value."""
        if self._instance is None:
            self._instance = self._import()
        return self._instance

    def _import(self) -> Any:
        import_string = import_attribute("flaxon.utils.import_string", "import_string")

        return import_string(self.import_path)


class ContextualProvider(Provider):
    """Resolve a dependency only when its context predicate permits it."""

    def __init__(self, provider: Provider, context_provider: Callable[[], bool]) -> None:
        self.provider = provider
        self.context_provider = context_provider

    def get(self, container: Any) -> Any:
        """Resolve the provider when its predicate is true, otherwise return None."""
        if self.context_provider():
            return self.provider.get(container)
        return None


class DecoratedProvider(Provider):
    """Transform a resolved dependency through a decorator callable."""

    def __init__(self, provider: Provider, decorator: Callable[[Any], Any]) -> None:
        self.provider = provider
        self.decorator = decorator

    def get(self, container: Any) -> Any:
        """Resolve the provider and return its decorated value."""
        instance = self.provider.get(container)
        return self.decorator(instance)
