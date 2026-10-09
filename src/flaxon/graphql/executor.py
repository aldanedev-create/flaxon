from __future__ import annotations

import asyncio
from typing import Any

from .exceptions import GraphQLError
from .types import InterfaceType, List, NonNull, ObjectType, Scalar


async def execute(
    schema: Any,
    document: Any,
    context: Any = None,
    variables: dict[str, Any] | None = None,
    operation_name: str | None = None,
) -> dict[str, Any]:
    variables = variables or {}

    # Locate target operation
    operation = None
    fragments = {}

    for definition in document.definitions:
        kind = getattr(definition, "kind", type(definition).__name__)
        if kind == "FragmentDefinition" or hasattr(definition, "type_condition"):
            frag_name = definition.name.value if hasattr(definition.name, "value") else str(definition.name)
            fragments[frag_name] = definition
        elif kind == "OperationDefinition" or hasattr(definition, "selection_set"):
            if operation_name:
                op_name = (
                    definition.name.value
                    if definition.name and hasattr(definition.name, "value")
                    else str(definition.name or "")
                )
                if op_name == operation_name:
                    operation = definition
            elif operation is None:
                operation = definition

    if not operation:
        return {"errors": [{"message": "Operation to execute was not found."}]}

    op_type = getattr(operation, "operation", "query").lower()
    root_type = getattr(schema, op_type, None)

    if not root_type:
        return {"errors": [{"message": f"Schema does not support operation type '{op_type}'."}]}

    coerced_variables = resolve_variables(operation, variables)

    exec_context = {
        "schema": schema,
        "document": document,
        "fragments": fragments,
        "variables": coerced_variables,
        "context": context,
    }

    try:
        data = await execute_selection_set(
            exec_context=exec_context,
            selection_set=operation.selection_set,
            parent_type=root_type,
            root_value=None,
        )
        return {"data": data}
    except Exception as exc:
        return {"errors": [{"message": str(exc)}]}


async def execute_selection_set(
    exec_context: dict[str, Any],
    selection_set: Any,
    parent_type: Any,
    root_value: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for selection in selection_set.selections:
        if should_skip(selection, exec_context["variables"]):
            continue

        kind = getattr(selection, "kind", type(selection).__name__)

        # Field execution
        if kind == "Field" or kind == "FieldNode" or hasattr(selection, "alias"):
            field_name = selection.name.value if hasattr(selection.name, "value") else str(selection.name)
            response_key = selection.alias.value if getattr(selection, "alias", None) else field_name

            # Introspection
            if field_name == "__typename":
                result[response_key] = parent_type.name
                continue

            field_def = (
                parent_type.fields.get(field_name)
                if isinstance(parent_type, (ObjectType, InterfaceType))
                else None
            )
            if not field_def:
                continue

            field_args = resolve_arguments(selection, exec_context["variables"])
            field_args = coerce_arguments(field_args, field_def.args)
            resolved_value = await resolve_field_value(
                field_def=field_def,
                parent_value=root_value,
                args=field_args,
                context=exec_context["context"],
                info={"field_name": field_name, "schema": exec_context["schema"]},
            )

            result[response_key] = await complete_value(
                exec_context=exec_context,
                field_type=field_def.type,
                selection=selection,
                value=resolved_value,
            )

        # Inline Fragment (... on Type)
        elif kind == "InlineFragment" or kind == "InlineFragmentNode" or hasattr(selection, "type_condition"):
            type_condition = (
                selection.type_condition.name.value
                if hasattr(selection.type_condition, "name")
                else str(selection.type_condition)
            )
            if type_condition == parent_type.name:
                fragment_res = await execute_selection_set(
                    exec_context=exec_context,
                    selection_set=selection.selection_set,
                    parent_type=parent_type,
                    root_value=root_value,
                )
                result.update(fragment_res)

        # Fragment Spread (... FragmentName)
        elif kind == "FragmentSpread" or kind == "FragmentSpreadNode" or hasattr(selection, "fragment_name"):
            frag_name = selection.name.value if hasattr(selection.name, "value") else str(selection.name)
            frag_def = exec_context["fragments"].get(frag_name)
            if frag_def:
                fragment_res = await execute_selection_set(
                    exec_context=exec_context,
                    selection_set=frag_def.selection_set,
                    parent_type=parent_type,
                    root_value=root_value,
                )
                result.update(fragment_res)

    return result


async def resolve_field_value(
    field_def: Any, parent_value: Any, args: dict[str, Any], context: Any, info: Any
) -> Any:
    if field_def.resolver and callable(field_def.resolver):
        res = field_def.resolver(parent_value, args, context, info)
        if asyncio.iscoroutine(res) or hasattr(res, "__await__"):
            return await res
        return res

    if isinstance(parent_value, dict):
        return parent_value.get(info["field_name"])
    if hasattr(parent_value, info["field_name"]):
        val = getattr(parent_value, info["field_name"])
        return val() if callable(val) else val

    return None


async def complete_value(exec_context: dict[str, Any], field_type: Any, selection: Any, value: Any) -> Any:
    if isinstance(field_type, NonNull):
        completed = await complete_value(exec_context, field_type.type, selection, value)
        if completed is None:
            raise GraphQLError("Cannot return null for non-nullable field.")
        return completed

    if value is None:
        return None

    if isinstance(field_type, List):
        if not isinstance(value, (list, tuple)):
            value = [value]
        return [await complete_value(exec_context, field_type.type, selection, item) for item in value]

    if isinstance(field_type, Scalar):
        return field_type.serialize(value)

    if isinstance(field_type, ObjectType):
        return await execute_selection_set(
            exec_context=exec_context,
            selection_set=selection.selection_set,
            parent_type=field_type,
            root_value=value,
        )

    return value


def should_skip(selection: Any, variables: dict[str, Any]) -> bool:
    directives = getattr(selection, "directives", []) or []
    for directive in directives:
        name = directive.name.value if hasattr(directive.name, "value") else str(directive.name)
        args = resolve_arguments(directive, variables)

        if name == "skip" and args.get("if") is True:
            return True
        if name == "include" and args.get("if") is False:
            return True
    return False


def resolve_arguments(node: Any, variables: dict[str, Any]) -> dict[str, Any]:
    args = {}
    node_args = getattr(node, "arguments", []) or []
    for arg in node_args:
        arg_name = arg.name.value if hasattr(arg.name, "value") else str(arg.name)
        args[arg_name] = resolve_value_node(arg.value, variables)
    return args


def coerce_arguments(args: dict[str, Any], definitions: dict[str, Any]) -> dict[str, Any]:
    """Coerce parsed argument values according to the field declaration."""
    coerced = dict(args)
    for name, type_def in definitions.items():
        if name not in coerced or coerced[name] is None:
            continue
        value = coerced[name]
        while isinstance(type_def, NonNull):
            type_def = type_def.type
        if isinstance(type_def, List):
            item_type = type_def.type
            values = value if isinstance(value, list) else [value]
            coerced[name] = [coerce_argument_value(item, item_type) for item in values]
        else:
            coerced[name] = coerce_argument_value(value, type_def)
    return coerced


def coerce_argument_value(value: Any, type_def: Any) -> Any:
    if isinstance(type_def, NonNull):
        return coerce_argument_value(value, type_def.type)
    if isinstance(type_def, List):
        return [
            coerce_argument_value(item, type_def.type)
            for item in (value if isinstance(value, list) else [value])
        ]
    if isinstance(type_def, Scalar):
        return type_def.parse_value(value)
    if type_def is int:
        return int(value)
    if type_def is float:
        return float(value)
    if type_def is bool:
        return value if isinstance(value, bool) else str(value).lower() == "true"
    if type_def is str:
        return str(value)
    return value


def resolve_value_node(value_node: Any, variables: dict[str, Any]) -> Any:
    kind = getattr(value_node, "kind", type(value_node).__name__)
    if kind == "VariableNode" or kind == "Variable" or hasattr(value_node, "variable"):
        var_name = value_node.name.value if hasattr(value_node.name, "value") else str(value_node.name)
        return variables.get(var_name)
    if hasattr(value_node, "value"):
        return value_node.value
    return value_node


def resolve_variables(operation: Any, variables: dict[str, Any]) -> dict[str, Any]:
    coerced = {}
    var_defs = getattr(operation, "variable_definitions", []) or []
    for var_def in var_defs:
        # The parser stores VariableDefinition.name directly. Keep support for
        # ASTs that wrap it in a Variable node as well.
        variable = getattr(var_def, "variable", None)
        name_node = variable if variable is not None else getattr(var_def, "name", None)
        if hasattr(name_node, "name"):
            name_node = name_node.name
        var_name = name_node.value if hasattr(name_node, "value") else str(name_node)
        if var_name in variables:
            coerced[var_name] = variables[var_name]
        elif hasattr(var_def, "default_value") and var_def.default_value:
            coerced[var_name] = resolve_value_node(var_def.default_value, {})
    return coerced
