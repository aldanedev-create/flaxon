from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from .cache import Cache
from .key_builder import KeyBuilder

F = TypeVar("F", bound=Callable[..., Any])

_default_cache: Cache | None = None


def get_default_cache() -> Cache:
    global _default_cache
    if _default_cache is None:
        _default_cache = Cache()
    return _default_cache


def cached(
    ttl: int | None = None,
    key_builder: KeyBuilder | None = None,
    cache: Cache | None = None,
) -> Callable[[F], F]:
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

            asyncio.create_task(cache_obj.set(key, result, ttl))
            return result

        return wrapper

    return decorator


def cached_async(
    ttl: int | None = None,
    key_builder: KeyBuilder | None = None,
    cache: Cache | None = None,
) -> Callable[[F], F]:
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
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_obj = cache or get_default_cache()
            builder = key_builder or KeyBuilder()

            key = builder.build_hash_from_func(func, *args, **kwargs)
            asyncio.create_task(cache_obj.delete(key))

            return func(*args, **kwargs)

        return wrapper

    return decorator


def invalidate_pattern(
    pattern: str,
    cache: Cache | None = None,
) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            return result

        return wrapper

    return decorator


def cache_result(
    ttl: int | None = None,
    key_prefix: str | None = None,
) -> Callable[[F], F]:
    builder = KeyBuilder(prefix=key_prefix or "result")
    return cached(ttl=ttl, key_builder=builder)


def cache_method(
    ttl: int | None = None,
    key_prefix: str | None = None,
) -> Callable[[F], F]:
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
