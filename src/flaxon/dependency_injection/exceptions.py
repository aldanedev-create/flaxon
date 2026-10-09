from __future__ import annotations

from flaxon.exceptions import FlaxonError


class DependencyError(FlaxonError):
    """Base exception for dependency registration or resolution failures."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class DependencyNotFoundError(DependencyError):
    """A requested dependency has no registered provider."""

    def __init__(self, message: str = "Dependency not found") -> None:
        super().__init__(message)


class CircularDependencyError(DependencyError):
    """Dependency resolution encountered a cyclic dependency."""

    def __init__(self, message: str = "Circular dependency detected") -> None:
        super().__init__(message)


class ProviderError(DependencyError):
    """A dependency provider failed to produce its value."""

    def __init__(self, message: str = "Provider error") -> None:
        super().__init__(message)


class ScopeError(DependencyError):
    """A dependency scope operation could not be completed."""

    def __init__(self, message: str = "Scope error") -> None:
        super().__init__(message)


class InjectionError(DependencyError):
    """Dependencies could not be injected into a callable."""

    def __init__(self, message: str = "Injection error") -> None:
        super().__init__(message)
