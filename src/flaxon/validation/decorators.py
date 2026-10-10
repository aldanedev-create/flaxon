from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from .coercion import coerce
from .schema import Schema

F = TypeVar("F", bound=Callable[..., Any])


def validate(schema_class: type[Schema]) -> Callable[[F], F]:
    """Check the supplied value against the configured constraints."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            sig = inspect.signature(func)
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()

            for name, value in bound_args.arguments.items():
                param = sig.parameters[name]
                annotation = param.annotation

                if (
                    annotation is not inspect.Parameter.empty
                    and (isinstance(annotation, type) and issubclass(annotation, Schema))
                    and isinstance(value, dict)
                ):
                    bound_args.arguments[name] = annotation.load(value)
                elif isinstance(value, annotation):
                    bound_args.arguments[name] = value
                else:
                    bound_args.arguments[name] = annotation.load(value)

            if inspect.iscoroutinefunction(func):
                return await func(*bound_args.args, **bound_args.kwargs)
            return func(*bound_args.args, **bound_args.kwargs)

        return wrapper

    return decorator


def validate_body(schema_class: type[Schema]) -> Callable[[F], F]:
    """Validate the body."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            sig = inspect.signature(func)
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()

            for name, value in bound_args.arguments.items():
                param = sig.parameters[name]
                annotation = param.annotation

                if (
                    annotation is not inspect.Parameter.empty
                    and (isinstance(annotation, type) and issubclass(annotation, Schema))
                    and (value is None)
                ):
                    bound_args.arguments[name] = None
                elif isinstance(value, dict):
                    bound_args.arguments[name] = annotation.load(value)
                else:
                    bound_args.arguments[name] = annotation.load(value)

            if inspect.iscoroutinefunction(func):
                return await func(*bound_args.args, **bound_args.kwargs)
            return func(*bound_args.args, **bound_args.kwargs)

        return wrapper

    return decorator


def validate_query(schema_class: type[Schema]) -> Callable[[F], F]:
    """Validate the query."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = None
            for arg in args:
                if hasattr(arg, "query"):
                    request = arg
                    break
            if request is None:
                for _name, value in kwargs.items():
                    if hasattr(value, "query"):
                        request = value
                        break

            if request is not None:
                query_data = request.query.to_dict()
                validated = schema_class.load(query_data)
                kwargs["validated_query"] = validated

            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def validate_params(schema_class: type[Schema]) -> Callable[[F], F]:
    """Validate the params."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = None
            for arg in args:
                if hasattr(arg, "path_params"):
                    request = arg
                    break
            if request is None:
                for _name, value in kwargs.items():
                    if hasattr(value, "path_params"):
                        request = value
                        break

            if request is not None:
                param_data = request.path_params
                validated = schema_class.load(param_data)
                kwargs["validated_params"] = validated

            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _coercion_types(signature, declared_types):
    param_names = list(signature.parameters.keys())
    type_mapping = {}

    for idx, param_name in enumerate(param_names):
        if idx < len(declared_types):
            type_mapping[param_name] = declared_types[idx]
        elif param_name in signature.parameters:
            annotation = signature.parameters[param_name].annotation
            if annotation is not inspect.Parameter.empty:
                type_mapping[param_name] = annotation
    return type_mapping


def coerce_params(*types: type) -> Callable[[F], F]:
    """Convert arguments using explicit types or function parameter annotations."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            sig = inspect.signature(func)
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()

            type_mapping = _coercion_types(sig, types)

            for name, value in bound_args.arguments.items():
                if name in type_mapping and value is not None:
                    target_type = type_mapping[name]
                    if not isinstance(value, target_type) and target_type in (
                        str,
                        int,
                        float,
                        bool,
                        list,
                        dict,
                    ):
                        bound_args.arguments[name] = coerce(value, target_type)

            if inspect.iscoroutinefunction(func):
                return await func(*bound_args.args, **bound_args.kwargs)
            return func(*bound_args.args, **bound_args.kwargs)

        return wrapper

    return decorator


def revalidate(func: F) -> F:
    """Perform the revalidate operation for this subsystem."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result

        if isinstance(result, Schema):
            result.validate()
        elif isinstance(result, list):
            for item in result:
                if isinstance(item, Schema):
                    item.validate()
        elif isinstance(result, dict):
            for value in result.values():
                if isinstance(value, Schema):
                    value.validate()

        return result

    return wrapper
