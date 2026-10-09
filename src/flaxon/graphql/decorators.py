from __future__ import annotations

from functools import wraps
from typing import Any


def graphql_type(name: str, description: str | None = None):
    def decorator(cls: type) -> type:
        cls._graphql_name = name
        cls._graphql_description = description
        return cls
    return decorator


def graphql_field(description: str | None = None):
    def decorator(func: Any) -> Any:
        func._graphql_field = True
        func._graphql_description = description
        return func
    return decorator


def graphql_query(name: str | None = None, description: str | None = None):
    def decorator(func: Any) -> Any:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)
        wrapper._graphql_query = True
        wrapper._graphql_name = name or func.__name__
        wrapper._graphql_description = description
        return wrapper
    return decorator


def graphql_mutation(name: str | None = None, description: str | None = None):
    def decorator(func: Any) -> Any:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)
        wrapper._graphql_mutation = True
        wrapper._graphql_name = name or func.__name__
        wrapper._graphql_description = description
        return wrapper
    return decorator


def graphql_subscription(name: str | None = None, description: str | None = None):
    def decorator(func: Any) -> Any:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)
        wrapper._graphql_subscription = True
        wrapper._graphql_name = name or func.__name__
        wrapper._graphql_description = description
        return wrapper
    return decorator
