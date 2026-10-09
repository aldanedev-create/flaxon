from __future__ import annotations

import json
from typing import Any


async def graphql(
    schema: Any,
    query: str,
    variables: dict[str, Any] | None = None,
    context: Any = None,
    operation_name: str | None = None,
) -> dict[str, Any]:
    """Execute a GraphQL query against a schema. Shorthand for schema.execute(...)."""
    return await schema.execute(query, variables=variables, context=context, operation_name=operation_name)


def graphql_to_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}

    if isinstance(obj, dict):
        return obj

    if hasattr(obj, "to_dict"):
        return obj.to_dict()

    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}

    return {"value": obj}


def graphql_to_json(obj: Any) -> str:
    return json.dumps(graphql_to_dict(obj), default=str)


def graphql_format_error(message: str, line: int | None = None, column: int | None = None) -> dict[str, Any]:
    error = {"message": message}
    if line is not None and column is not None:
        error["locations"] = [{"line": line, "column": column}]
    return error


def graphql_is_valid_name(name: str) -> bool:
    import re
    return bool(re.match(r"^[_a-zA-Z][_a-zA-Z0-9]*$", name))


def graphql_sanitize_name(name: str) -> str:
    import re
    return re.sub(r"[^_a-zA-Z0-9]", "_", name)


def graphql_get_field_names(obj: Any) -> list[str]:
    if obj is None:
        return []

    if hasattr(obj, "_graphql_fields"):
        return list(obj._graphql_fields.keys())

    if isinstance(obj, dict):
        return list(obj.keys())

    if hasattr(obj, "__dict__"):
        return [k for k in obj.__dict__.keys() if not k.startswith("_")]

    return []


def graphql_get_value(obj: Any, field: str) -> Any:
    if obj is None:
        return None

    if isinstance(obj, dict):
        return obj.get(field)

    if hasattr(obj, field):
        attr = getattr(obj, field)
        if callable(attr):
            return attr()
        return attr

    return None


async def graphql_async_get_value(obj: Any, field: str) -> Any:
    value = graphql_get_value(obj, field)
    if hasattr(value, "__await__"):
        return await value
    return value


def graphql_is_required_field(field: Any) -> bool:
    if hasattr(field, "required"):
        return field.required
    return False


def graphql_get_default_value(field: Any) -> Any:
    if hasattr(field, "default_value"):
        return field.default_value
    return None
