from __future__ import annotations

from typing import Any


class Field:
    """Validate and convert  field values."""

    def __init__(self, type_: Any, args: dict[str, Any] | None = None, resolver: Any = None) -> None:
        self.type = type_
        self.args = args or {}
        self.resolver = resolver
        self.name: str | None = None

    def resolve(self, parent: Any, args: dict[str, Any], context: Any, info: Any) -> Any:
        """Perform the resolve operation for field."""
        if self.resolver and callable(self.resolver):
            result = self.resolver(parent, args, context, info)
            if hasattr(result, "__await__"):
                return result
            return result

        return None


class InputField:
    """Validate and convert input field values."""

    def __init__(self, type_: Any, default_value: Any = None) -> None:
        self.type = type_
        self.default_value = default_value


class ObjectType:
    """Object type implementation for the graphql subsystem."""

    def __init__(self, name: str, fields: dict[str, Field], description: str | None = None) -> None:
        self.name = name
        self.fields = fields
        self.description = description
        self.interfaces: list[InterfaceType] = []

        for field_name, field in fields.items():
            field.name = field_name

    def add_interface(self, interface: InterfaceType) -> None:
        """Add the interface."""
        self.interfaces.append(interface)


class InterfaceType:
    """Interface type implementation for the graphql subsystem."""

    def __init__(self, name: str, fields: dict[str, Field], description: str | None = None) -> None:
        """Perform the   init   operation for interface type."""
        self.name = name
        self.fields = fields
        self.description = description

        for field_name, field in fields.items():
            field.name = field_name


class UnionType:
    """Union type implementation for the graphql subsystem."""

    def __init__(self, name: str, types: list[ObjectType], description: str | None = None) -> None:
        self.name = name
        self.types = types
        self.description = description


class InputObjectType:
    """Input object type implementation for the graphql subsystem."""

    def __init__(self, name: str, fields: dict[str, InputField], description: str | None = None) -> None:
        self.name = name
        self.fields = fields
        self.description = description


class List:
    """List implementation for the graphql subsystem."""

    def __init__(self, type_: Any) -> None:
        self.type = type_


class NonNull:
    """Non null implementation for the graphql subsystem."""

    def __init__(self, type_: Any) -> None:
        """Perform the   init   operation for non null."""
        self.type = type_


class Scalar:
    """Scalar implementation for the graphql subsystem."""

    def __init__(self, name: str, description: str | None = None) -> None:
        self.name = name
        self.description = description
        self._serialize = None
        self._parse_value = None
        self._parse_literal = None

    def serialize(self, value: Any) -> Any:
        """Convert the supplied value into its serialized representation."""
        if self._serialize:
            return self._serialize(value)
        return value

    def parse_value(self, value: Any) -> Any:
        """Parse the value."""
        if self._parse_value:
            return self._parse_value(value)
        return value

    def parse_literal(self, value: Any) -> Any:
        """Parse the literal."""
        if self._parse_literal:
            return self._parse_literal(value)
        return value

    def set_serialize(self, func: Any) -> None:
        """Set the serialize."""
        self._serialize = func

    def set_parse_value(self, func: Any) -> None:
        """Set the parse value."""
        self._parse_value = func

    def set_parse_literal(self, func: Any) -> None:
        """Set the parse literal."""
        self._parse_literal = func
