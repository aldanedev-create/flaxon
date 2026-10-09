from __future__ import annotations

from typing import Any

from .ast import Field, FragmentDefinition, FragmentSpread, OperationDefinition
from .exceptions import GraphQLValidationError
from .types import InterfaceType, List, NonNull, ObjectType


class ValidationRule:
    def __init__(self, name: str, validate_func: Any) -> None:
        self.name = name
        self.validate = validate_func


def validate_query(schema: Any, document: Any) -> list[GraphQLValidationError]:
    errors: list[GraphQLValidationError] = []

    rules = [
        ValidationRule("DocumentHasOperations", validate_has_operations),
        ValidationRule("OperationNameUniqueness", validate_operation_names_unique),
        ValidationRule("FieldSelectionsOnObjects", validate_fields_on_objects),
        ValidationRule("FragmentSpreadTargetDefined", validate_fragment_targets),
        ValidationRule("FragmentSpreadTypeExistence", validate_fragment_types),
        ValidationRule("VariablesAreInputTypes", validate_variable_types),
        ValidationRule("AllVariableUsagesDefined", validate_variable_usages),
        ValidationRule("DirectivesAreDefined", validate_directives),
    ]

    for rule in rules:
        try:
            errors.extend(rule.validate(schema, document))
        except Exception as exc:
            errors.append(GraphQLValidationError(f"Validation rule '{rule.name}' error: {exc}"))

    return errors


def validate_has_operations(schema: Any, document: Any) -> list[GraphQLValidationError]:
    has_ops = any(
        isinstance(definition, OperationDefinition)
        or getattr(definition, "kind", "") == "OperationDefinition"
        for definition in document.definitions
    )

    if not has_ops:
        return [GraphQLValidationError("Document must contain at least one operation.")]
    return []


def validate_operation_names_unique(schema: Any, document: Any) -> list[GraphQLValidationError]:
    names: set[str] = set()
    errors: list[GraphQLValidationError] = []

    for definition in document.definitions:
        if (
            isinstance(definition, OperationDefinition)
            or getattr(definition, "kind", "") == "OperationDefinition"
        ) and definition.name:
            op_name = definition.name.value if hasattr(definition.name, "value") else str(definition.name)
            if op_name in names:
                errors.append(GraphQLValidationError(f"Operation name '{op_name}' is not unique."))
            names.add(op_name)

    return errors


def validate_fields_on_objects(schema: Any, document: Any) -> list[GraphQLValidationError]:
    errors: list[GraphQLValidationError] = []

    def check_selection_set(selection_set: Any, parent_type: Any) -> None:
        if not selection_set or not hasattr(selection_set, "selections"):
            return

        for selection in selection_set.selections:
            kind = getattr(selection, "kind", type(selection).__name__)

            if kind == "Field" or isinstance(selection, Field) or hasattr(selection, "name"):
                field_name = selection.name.value if hasattr(selection.name, "value") else str(selection.name)

                # Introspection fields support
                if field_name in ("__schema", "__typename", "__type"):
                    continue

                if isinstance(parent_type, (ObjectType, InterfaceType)):
                    fields = parent_type.fields
                    if field_name not in fields:
                        errors.append(
                            GraphQLValidationError(
                                f"Cannot query field '{field_name}' on type '{parent_type.name}'."
                            )
                        )
                    else:
                        field_def = fields[field_name]
                        unwrapped = _unwrap_type(field_def.type)
                        if getattr(selection, "selection_set", None):
                            check_selection_set(selection.selection_set, unwrapped)

    for definition in document.definitions:
        if (
            isinstance(definition, OperationDefinition)
            or getattr(definition, "kind", "") == "OperationDefinition"
        ):
            op_type = getattr(definition, "operation", "query").lower()
            root_type = getattr(schema, op_type, None)
            if root_type and getattr(definition, "selection_set", None):
                check_selection_set(definition.selection_set, root_type)

    return errors


def validate_fragment_targets(schema: Any, document: Any) -> list[GraphQLValidationError]:
    errors: list[GraphQLValidationError] = []
    fragment_names = {
        (def_.name.value if hasattr(def_.name, "value") else str(def_.name))
        for def_ in document.definitions
        if getattr(def_, "kind", "") == "FragmentDefinition" or isinstance(def_, FragmentDefinition)
    }

    def check_selection_set(selection_set: Any) -> None:
        if not selection_set or not hasattr(selection_set, "selections"):
            return
        for selection in selection_set.selections:
            kind = getattr(selection, "kind", type(selection).__name__)
            if kind == "FragmentSpread" or isinstance(selection, FragmentSpread):
                spread_name = (
                    selection.name.value if hasattr(selection.name, "value") else str(selection.name)
                )
                if spread_name not in fragment_names:
                    errors.append(GraphQLValidationError(f"Unknown fragment '{spread_name}'."))
            nested = getattr(selection, "selection_set", None)
            if nested:
                check_selection_set(nested)

    for definition in document.definitions:
        selection_set = getattr(definition, "selection_set", None)
        if selection_set:
            check_selection_set(selection_set)

    return errors


def validate_fragment_types(schema: Any, document: Any) -> list[GraphQLValidationError]:
    errors: list[GraphQLValidationError] = []
    all_types = schema.get_types()

    for definition in document.definitions:
        if getattr(definition, "kind", "") == "FragmentDefinition" or isinstance(
            definition, FragmentDefinition
        ):
            type_condition = (
                definition.type_condition.name.value
                if hasattr(definition.type_condition, "name")
                else str(definition.type_condition)
            )
            if type_condition not in all_types:
                errors.append(
                    GraphQLValidationError(f"Unknown type condition '{type_condition}' on fragment.")
                )

    return errors


def validate_variable_types(schema: Any, document: Any) -> list[GraphQLValidationError]:
    errors: list[GraphQLValidationError] = []

    for definition in document.definitions:
        if hasattr(definition, "variable_definitions") and definition.variable_definitions:
            for var_def in definition.variable_definitions:
                var_type_name = _extract_type_name(var_def.type)
                type_obj = schema.get_type(var_type_name)
                if not type_obj and var_type_name not in ("String", "Int", "Float", "Boolean", "ID"):
                    variable = getattr(var_def, "variable", None)
                    name_node = variable if variable is not None else getattr(var_def, "name", None)
                    if hasattr(name_node, "name"):
                        name_node = name_node.name
                    var_name = name_node.value if hasattr(name_node, "value") else str(name_node)
                    errors.append(
                        GraphQLValidationError(f"Variable '${var_name}' has unknown type '{var_type_name}'.")
                    )

    return errors


def validate_variable_usages(schema: Any, document: Any) -> list[GraphQLValidationError]:
    return []


def validate_directives(schema: Any, document: Any) -> list[GraphQLValidationError]:
    errors: list[GraphQLValidationError] = []
    valid_directives = {d.name for d in schema.get_directives()}

    def check_directives(node: Any) -> None:
        directives = getattr(node, "directives", []) or []
        for directive in directives:
            dir_name = directive.name.value if hasattr(directive.name, "value") else str(directive.name)
            if dir_name not in valid_directives:
                errors.append(GraphQLValidationError(f"Unknown directive '@{dir_name}'."))

        selection_set = getattr(node, "selection_set", None)
        if selection_set and hasattr(selection_set, "selections"):
            for sel in selection_set.selections:
                check_directives(sel)

    for definition in document.definitions:
        check_directives(definition)

    return errors


def _unwrap_type(type_obj: Any) -> Any:
    while isinstance(type_obj, (NonNull, List)):
        type_obj = type_obj.type
    return type_obj


def _extract_type_name(type_node: Any) -> str:
    if hasattr(type_node, "name"):
        return type_node.name.value if hasattr(type_node.name, "value") else str(type_node.name)
    if hasattr(type_node, "type"):
        return _extract_type_name(type_node.type)
    return str(type_node)
