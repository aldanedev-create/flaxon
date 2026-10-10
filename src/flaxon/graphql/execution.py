from __future__ import annotations

from typing import Any

from flaxon._imports import import_attribute

from .exceptions import GraphQLExecutionError
from .types import List, NonNull


async def execute(
    schema: Any,
    document: Any,
    context: Any = None,
    variables: dict[str, Any] | None = None,
    operation_name: str | None = None,
) -> dict[str, Any]:
    """Execute the supplied operation with its parameters."""
    variables = variables or {}

    operation = None
    for definition in document.definitions:
        if hasattr(definition, "operation") and (operation_name is None or definition.name == operation_name):
            operation = definition
            break

    if operation is None:
        raise GraphQLExecutionError("No valid operation found")

    root_type = None
    if operation.operation == "query":
        root_type = schema.query
    elif operation.operation == "mutation":
        root_type = schema.mutation
    elif operation.operation == "subscription":
        root_type = schema.subscription

    if root_type is None:
        raise GraphQLExecutionError(f"Root type '{operation.operation}' is not defined")

    result = await execute_selection_set(
        root_type,
        operation.selection_set,
        None,
        context,
        variables,
        schema,
    )

    return {"data": result}


async def execute_selection_set(  # noqa: PLR0917 - preserve existing positional API
    parent_type: Any,
    selection_set: Any,
    parent_value: Any,
    context: Any,
    variables: dict[str, Any],
    schema: Any,
) -> dict[str, Any]:
    """Execute the selection set."""
    result = {}

    for selection in selection_set.selections:
        if hasattr(selection, "field"):
            result.update(
                await _execute_selected_field(
                    selection,
                    parent_type=parent_type,
                    parent_value=parent_value,
                    context=context,
                    variables=variables,
                    schema=schema,
                )
            )

        elif hasattr(selection, "inline_fragment"):
            type_condition = getattr(selection, "type_condition", None)
            if type_condition is not None:
                type_name = type_condition.name.value
                if schema.get_type(type_name):
                    fragment_type = schema.get_type(type_name)
                    fragment_result = await execute_selection_set(
                        fragment_type,
                        selection.selection_set,
                        parent_value,
                        context,
                        variables,
                        schema,
                    )
                    result.update(fragment_result)

        elif hasattr(selection, "fragment_spread"):
            fragment_name = selection.fragment_name.name.value
            fragment = None
            for definition in schema._fragments or []:
                if definition.name.value == fragment_name:
                    fragment = definition
                    break

            if fragment is not None:
                fragment_result = await execute_selection_set(
                    parent_type,
                    fragment.selection_set,
                    parent_value,
                    context,
                    variables,
                    schema,
                )
                result.update(fragment_result)

    return result


async def _execute_selected_field(selection, *, parent_type, parent_value, context, variables, schema):
    result = {}
    field_name = selection.field.name.value
    field_args = selection.field.arguments

    field_def = parent_type.fields.get(field_name)
    if field_def is None:
        return {}

    args = {}
    for arg in field_args:
        arg_value = await evaluate_value(arg.value, variables, context)
        args[arg.name.value] = arg_value

    field_type = field_def.type

    resolved_value = await resolve_field_value(
        parent_type.name,
        field_name,
        parent_value,
        args,
        context,
        schema,
    )

    if field_type is not None:
        if isinstance(field_type, NonNull):
            field_type = field_type.type

        if isinstance(field_type, List):
            if resolved_value is not None:
                if not isinstance(resolved_value, list):
                    resolved_value = [resolved_value]
                for i, item in enumerate(resolved_value):
                    resolved_value[i] = await coerce_value(item, field_type.type)
            result[field_name] = resolved_value
        else:
            result[field_name] = await coerce_value(resolved_value, field_type)
    return result


async def resolve_field_value(  # noqa: PLR0917 - preserve existing positional API
    type_name: str,
    field_name: str,
    parent_value: Any,
    args: dict[str, Any],
    context: Any,
    schema: Any,
) -> Any:
    """Resolve the field value."""
    resolver = schema.resolver()
    info = type(
        "Info",
        (),
        {
            "field_name": field_name,
            "parent_type": type_name,
            "context": context,
        },
    )

    return await resolver.resolve(
        type_name,
        field_name,
        parent_value,
        args,
        context,
        info,
    )


async def coerce_value(value: Any, field_type: Any) -> Any:
    """Coerce the value."""
    if value is None:
        return None

    if hasattr(field_type, "serialize"):
        return field_type.serialize(value)

    if hasattr(field_type, "resolve"):
        result = field_type.resolve(value)
        if hasattr(result, "__await__"):
            return await result
        return result

    return value


async def evaluate_value(value_node: Any, variables: dict[str, Any], context: Any) -> Any:
    """Perform the evaluate value operation for this subsystem."""
    boolean_value_type = import_attribute("flaxon.graphql.ast", "BooleanValue")
    float_value_type = import_attribute("flaxon.graphql.ast", "FloatValue")
    int_value_type = import_attribute("flaxon.graphql.ast", "IntValue")
    list_value_type = import_attribute("flaxon.graphql.ast", "ListValue")
    object_value_type = import_attribute("flaxon.graphql.ast", "ObjectValue")
    string_value_type = import_attribute("flaxon.graphql.ast", "StringValue")
    variable_type = import_attribute("flaxon.graphql.ast", "Variable")

    for value_type, convert in ((int_value_type, int), (float_value_type, float)):
        if isinstance(value_node, value_type):
            return convert(value_node.value)
    if isinstance(value_node, (string_value_type, boolean_value_type)):
        return value_node.value

    if isinstance(value_node, variable_type):
        return variables.get(value_node.name.value)

    if isinstance(value_node, list_value_type):
        return [await evaluate_value(v, variables, context) for v in value_node.values]

    if isinstance(value_node, object_value_type):
        result = {}
        for field in value_node.fields:
            result[field.name.value] = await evaluate_value(field.value, variables, context)
        return result

    return value_node


def coerce_variable_value(value: Any, type_def: Any) -> Any:
    """Coerce the variable value."""
    if value is None:
        return None

    if hasattr(type_def, "parse_value"):
        return type_def.parse_value(value)

    if hasattr(type_def, "parse_literal"):
        return type_def.parse_literal(value)

    return value
