from __future__ import annotations

from typing import Any


class Schema:
    """Schema implementation for the openapi subsystem."""

    def __init__(self) -> None:
        self._schema: dict[str, Any] = {}

    def type(self, type_: str) -> Schema:
        """Perform the type operation for schema."""
        self._schema["type"] = type_
        return self

    def string(self) -> Schema:
        """Perform the string operation for schema."""
        return self.type("string")

    def integer(self) -> Schema:
        """Perform the integer operation for schema."""
        return self.type("integer")

    def number(self) -> Schema:
        """Perform the number operation for schema."""
        return self.type("number")

    def boolean(self) -> Schema:
        """Perform the boolean operation for schema."""
        return self.type("boolean")

    def array(self, items: dict[str, Any] | None = None) -> Schema:
        """Perform the array operation for schema."""
        self.type("array")
        if items:
            self._schema["items"] = items
        return self

    def object(self, properties: dict[str, Any] | None = None) -> Schema:
        """Perform the object operation for schema."""
        self.type("object")
        if properties:
            self._schema["properties"] = properties
        return self

    def required(self, *fields: str) -> Schema:
        """Configure whether a value must be supplied."""
        self._schema["required"] = list(fields)
        return self

    def description(self, description: str) -> Schema:
        """Perform the description operation for schema."""
        self._schema["description"] = description
        return self

    def enum(self, *values: Any) -> Schema:
        """Perform the enum operation for schema."""
        self._schema["enum"] = list(values)
        return self

    def nullable(self, nullable: bool = True) -> Schema:
        """Configure whether null values are accepted."""
        self._schema["nullable"] = nullable
        return self

    def default(self, default: Any) -> Schema:
        """Configure the fallback value."""
        self._schema["default"] = default
        return self

    def min_length(self, min_length: int) -> Schema:
        """Perform the min length operation for schema."""
        self._schema["minLength"] = min_length
        return self

    def max_length(self, max_length: int) -> Schema:
        """Perform the max length operation for schema."""
        self._schema["maxLength"] = max_length
        return self

    def minimum(self, minimum: float) -> Schema:
        """Perform the minimum operation for schema."""
        self._schema["minimum"] = minimum
        return self

    def maximum(self, maximum: float) -> Schema:
        """Perform the maximum operation for schema."""
        self._schema["maximum"] = maximum
        return self

    def pattern(self, pattern: str) -> Schema:
        """Perform the pattern operation for schema."""
        self._schema["pattern"] = pattern
        return self

    def format(self, format: str) -> Schema:
        """Perform the format operation for schema."""
        self._schema["format"] = format
        return self

    def example(self, example: Any) -> Schema:
        """Perform the example operation for schema."""
        self._schema["example"] = example
        return self

    def build(self) -> dict[str, Any]:
        """Perform the build operation for schema."""
        return self._schema


class SchemaBuilder:
    """Schema builder implementation for the openapi subsystem."""

    @staticmethod
    def string() -> dict[str, Any]:
        """Perform the string operation for schema builder."""
        return Schema().string().build()

    @staticmethod
    def integer() -> dict[str, Any]:
        """Perform the integer operation for schema builder."""
        return Schema().integer().build()

    @staticmethod
    def number() -> dict[str, Any]:
        """Perform the number operation for schema builder."""
        return Schema().number().build()

    @staticmethod
    def boolean() -> dict[str, Any]:
        """Perform the boolean operation for schema builder."""
        return Schema().boolean().build()

    @staticmethod
    def array(items: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform the array operation for schema builder."""
        return Schema().array(items).build()

    @staticmethod
    def object(properties: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform the object operation for schema builder."""
        return Schema().object(properties).build()

    @staticmethod
    def from_field(field: Any) -> dict[str, Any]:
        """Build an OpenAPI schema from a Flaxon validation field."""
        schema = Schema()
        field_type = type(field).__name__.lower()
        configure = {
            "strfield": SchemaBuilder._string_field,
            "intfield": SchemaBuilder._integer_field,
            "floatfield": SchemaBuilder._number_field,
            "decimalfield": SchemaBuilder._number_field,
            "choicefield": SchemaBuilder._choice_field,
            "listfield": SchemaBuilder._list_field,
            "nestedfield": SchemaBuilder._nested_field,
            "boolfield": lambda item, result: result.boolean(),
            "emailfield": lambda item, result: result.string().format("email"),
            "datefield": lambda item, result: result.string().format("date"),
            "datetimefield": lambda item, result: result.string().format("date-time"),
            "uuidfield": lambda item, result: result.string().format("uuid"),
        }.get(field_type)
        if configure is not None:
            configure(field, schema)
        return schema.build()

    @staticmethod
    def _string_field(field: Any, schema: Schema) -> None:
        schema.string()
        if getattr(field, "min_length", None) is not None:
            schema.min_length(field.min_length)
        if getattr(field, "max_length", None) is not None:
            schema.max_length(field.max_length)

    @staticmethod
    def _numeric_bounds(field: Any, schema: Schema) -> None:
        if getattr(field, "minimum", None) is not None:
            schema.minimum(field.minimum)
        if getattr(field, "maximum", None) is not None:
            schema.maximum(field.maximum)

    @staticmethod
    def _integer_field(field: Any, schema: Schema) -> None:
        schema.integer()
        SchemaBuilder._numeric_bounds(field, schema)

    @staticmethod
    def _number_field(field: Any, schema: Schema) -> None:
        schema.number()
        SchemaBuilder._numeric_bounds(field, schema)

    @staticmethod
    def _choice_field(field: Any, schema: Schema) -> None:
        choices = list(getattr(field, "choices", []))
        if not choices:
            return
        first_type = type(choices[0])
        configure = {int: schema.integer, float: schema.number, bool: schema.boolean}.get(
            first_type, schema.string
        )
        configure()
        schema.enum(*choices)

    @staticmethod
    def _list_field(field: Any, schema: Schema) -> None:
        item_field = getattr(field, "item_field", None)
        schema.array(SchemaBuilder.from_field(item_field) if item_field is not None else {})
        if getattr(field, "min_items", None) is not None:
            schema._schema["minItems"] = field.min_items
        if getattr(field, "max_items", None) is not None:
            schema._schema["maxItems"] = field.max_items

    @staticmethod
    def _nested_field(field: Any, schema: Schema) -> None:
        nested = getattr(field, "schema_class", None)
        if nested is None:
            return
        child_fields = getattr(nested, "__fields__", {})
        schema.object({name: SchemaBuilder.from_field(child) for name, child in child_fields.items()})
        required = [name for name, child in child_fields.items() if getattr(child, "required", False)]
        if required:
            schema.required(*required)
