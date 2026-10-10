from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import cache as singleton, wraps
from typing import Any, TypeVar

from .cache import Cache
from .key_builder import KeyBuilder

F = TypeVar("F", bound=Callable[..., Any])


@singleton
def get_default_cache() -> Cache:
    """Return the shared default cache, creating it on first access."""
    return Cache()


def cached(
    ttl: int | None = None,
    key_builder: KeyBuilder | None = None,
    cache: Cache | None = None,
) -> Callable[[F], F]:
    """Cache the result of a synchronous callable using its argument-derived key."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_obj = cache or get_default_cache()
            builder = key_builder or KeyBuilder()

            key = builder.build_hash_from_func(func, *args, **kwargs)

            cached_value = asyncio.run(cache_obj.get(key))
            if cached_value is not None:
                return cached_value

            result = func(*args, **kwargs)

            if asyncio.iscoroutine(result):
                return result

            asyncio.run(cache_obj.set(key, result, ttl))
            return result

        return wrapper

    return decorator


def cached_async(
    ttl: int | None = None,
    key_builder: KeyBuilder | None = None,
    cache: Cache | None = None,
) -> Callable[[F], F]:
    """Cache the awaited result of an asynchronous callable."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_obj = cache or get_default_cache()
            builder = key_builder or KeyBuilder()

            key = builder.build_hash_from_func(func, *args, **kwargs)

            cached_value = await cache_obj.get(key)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)

            await cache_obj.set(key, result, ttl)
            return result

        return wrapper

    return decorator


def invalidate_cache(
    key_builder: KeyBuilder | None = None,
    cache: Cache | None = None,
) -> Callable[[F], F]:
    """Remove the argument-derived cache entry before calling the wrapped function."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_obj = cache or get_default_cache()
            builder = key_builder or KeyBuilder()

            key = builder.build_hash_from_func(func, *args, **kwargs)
            asyncio.run(cache_obj.delete(key))

            return func(*args, **kwargs)

        return wrapper

    return decorator


def invalidate_pattern(
    pattern: str,
    cache: Cache | None = None,
) -> Callable[[F], F]:
    """Preserve the pattern-invalidation API; pattern removal is not implemented."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Perform the wrapper operation for this subsystem."""
            return func(*args, **kwargs)

        return wrapper

    return decorator


def cache_result(
    ttl: int | None = None,
    key_prefix: str | None = None,
) -> Callable[[F], F]:
    """Cache callable results with the supplied key prefix and expiry."""
    builder = KeyBuilder(prefix=key_prefix or "result")
    return cached(ttl=ttl, key_builder=builder)


def cache_method(
    ttl: int | None = None,
    key_prefix: str | None = None,
) -> Callable[[F], F]:
    """Cache an asynchronous method's result using a class-specific key."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            cache_obj = get_default_cache()
            prefix = key_prefix or func.__name__
            builder = KeyBuilder(prefix=prefix)

            class_name = self.__class__.__name__
            key = builder.build_hash(class_name, *args, **kwargs)

            cached_value = await cache_obj.get(key)
            if cached_value is not None:
                return cached_value

            result = await func(self, *args, **kwargs)

            await cache_obj.set(key, result, ttl)
            return result

        return wrapper

    return decorator
