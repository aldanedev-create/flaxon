from __future__ import annotations

from flaxon.exceptions import FlaxonError


class CacheError(FlaxonError):
    """Base exception for cache operation failures."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class CacheKeyError(CacheError):
    """A cache key is invalid for the requested operation."""

    def __init__(self, message: str = "Invalid cache key") -> None:
        super().__init__(message)


class CacheNotFoundError(CacheError):
    """A required cache entry could not be found."""

    def __init__(self, message: str = "Cache entry not found") -> None:
        super().__init__(message)


class CacheTimeoutError(CacheError):
    """A cache operation exceeded its allowed duration."""

    def __init__(self, message: str = "Cache operation timed out") -> None:
        super().__init__(message)


class CacheSerializationError(CacheError):
    """A cache value could not be encoded or decoded."""

    def __init__(self, message: str = "Cache serialization error") -> None:
        super().__init__(message)
