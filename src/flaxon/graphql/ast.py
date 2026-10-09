from __future__ import annotations

from typing import Any


class Node:
    def __init__(self, kind: str) -> None:
        self.kind = kind


class Document(Node):
    def __init__(self, definitions: list[Any]) -> None:
        super().__init__("Document")
        self.definitions = definitions


class OperationDefinition(Node):
    def __init__(
        self,
        operation: str,
        name: Any = None,
        variable_definitions: list[Any] = None,
        directives: list[Any] = None,
        selection_set: Any = None,
    ) -> None:
        super().__init__("OperationDefinition")
        self.operation = operation
        self.name = name
        self.variable_definitions = variable_definitions or []
        self.directives = directives or []
        self.selection_set = selection_set


class SelectionSet(Node):
    def __init__(self, selections: list[Any]) -> None:
        super().__init__("SelectionSet")
        self.selections = selections


class Field(Node):
    def __init__(
        self,
        name: Any,
        alias: Any = None,
        arguments: list[Any] = None,
        directives: list[Any] = None,
        selection_set: Any = None,
    ) -> None:
        super().__init__("Field")
        self.name = name
        self.alias = alias
        self.arguments = arguments or []
        self.directives = directives or []
        self.selection_set = selection_set


class FragmentSpread(Node):
    def __init__(self, name: Any, directives: list[Any] = None) -> None:
        super().__init__("FragmentSpread")
        self.name = name
        self.directives = directives or []


class InlineFragment(Node):
    def __init__(
        self,
        type_condition: Any = None,
        directives: list[Any] = None,
        selection_set: Any = None,
    ) -> None:
        super().__init__("InlineFragment")
        self.type_condition = type_condition
        self.directives = directives or []
        self.selection_set = selection_set


class FragmentDefinition(Node):
    def __init__(
        self,
        name: Any,
        type_condition: Any,
        directives: list[Any] = None,
        selection_set: Any = None,
    ) -> None:
        super().__init__("FragmentDefinition")
        self.name = name
        self.type_condition = type_condition
        self.directives = directives or []
        self.selection_set = selection_set


class VariableDefinition(Node):
    def __init__(self, name: Any, type: Any, default_value: Any = None) -> None:
        super().__init__("VariableDefinition")
        self.name = name
        self.type = type
        self.default_value = default_value


class Variable(Node):
    def __init__(self, name: Any) -> None:
        super().__init__("Variable")
        self.name = name


class Name(Node):
    def __init__(self, value: str) -> None:
        super().__init__("Name")
        self.value = value


class Argument(Node):
    def __init__(self, name: Any, value: Any) -> None:
        super().__init__("Argument")
        self.name = name
        self.value = value


class Directive(Node):
    def __init__(self, name: Any, arguments: list[Any] = None) -> None:
        super().__init__("Directive")
        self.name = name
        self.arguments = arguments or []


class NamedType(Node):
    def __init__(self, name: Any) -> None:
        super().__init__("NamedType")
        self.name = name


class ListType(Node):
    def __init__(self, type: Any) -> None:
        super().__init__("ListType")
        self.type = type


class NonNullType(Node):
    def __init__(self, type: Any) -> None:
        super().__init__("NonNullType")
        self.type = type


class IntValue(Node):
    def __init__(self, value: str) -> None:
        super().__init__("IntValue")
        self.value = value


class FloatValue(Node):
    def __init__(self, value: str) -> None:
        super().__init__("FloatValue")
        self.value = value


class StringValue(Node):
    def __init__(self, value: str) -> None:
        super().__init__("StringValue")
        self.value = value


class BooleanValue(Node):
    def __init__(self, value: bool) -> None:
        super().__init__("BooleanValue")
        self.value = value


class ListValue(Node):
    def __init__(self, values: list[Any]) -> None:
        super().__init__("ListValue")
        self.values = values


class ObjectValue(Node):
    def __init__(self, fields: list[Any]) -> None:
        super().__init__("ObjectValue")
        self.fields = fields


class ObjectField(Node):
    def __init__(self, name: Any, value: Any) -> None:
        super().__init__("ObjectField")
        self.name = name
        self.value = value
