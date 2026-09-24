from __future__ import annotations

from typing import Any


class Schema:
    def __init__(self) -> None:
        self._schema: dict[str, Any] = {}

    def type(self, type_: str) -> Schema:
        self._schema["type"] = type_
        return self

    def string(self) -> Schema:
        return self.type("string")

    def integer(self) -> Schema:
        return self.type("integer")

    def number(self) -> Schema:
        return self.type("number")

    def boolean(self) -> Schema:
        return self.type("boolean")

    def array(self, items: dict[str, Any] | None = None) -> Schema:
        self.type("array")
        if items:
            self._schema["items"] = items
        return self

    def object(self, properties: dict[str, Any] | None = None) -> Schema:
        self.type("object")
        if properties:
            self._schema["properties"] = properties
        return self

    def required(self, *fields: str) -> Schema:
        self._schema["required"] = list(fields)
        return self

    def description(self, description: str) -> Schema:
        self._schema["description"] = description
        return self

    def enum(self, *values: Any) -> Schema:
        self._schema["enum"] = list(values)
        return self

    def nullable(self, nullable: bool = True) -> Schema:
        self._schema["nullable"] = nullable
        return self

    def default(self, default: Any) -> Schema:
        self._schema["default"] = default
        return self

    def min_length(self, min_length: int) -> Schema:
        self._schema["minLength"] = min_length
        return self

    def max_length(self, max_length: int) -> Schema:
        self._schema["maxLength"] = max_length
        return self

    def minimum(self, minimum: float) -> Schema:
        self._schema["minimum"] = minimum
        return self

    def maximum(self, maximum: float) -> Schema:
        self._schema["maximum"] = maximum
        return self

    def pattern(self, pattern: str) -> Schema:
        self._schema["pattern"] = pattern
        return self

    def format(self, format: str) -> Schema:
        self._schema["format"] = format
        return self

    def example(self, example: Any) -> Schema:
        self._schema["example"] = example
        return self

    def build(self) -> dict[str, Any]:
        return self._schema


class SchemaBuilder:
    @staticmethod
    def string() -> dict[str, Any]:
        return Schema().string().build()

    @staticmethod
    def integer() -> dict[str, Any]:
        return Schema().integer().build()

    @staticmethod
    def number() -> dict[str, Any]:
        return Schema().number().build()

    @staticmethod
    def boolean() -> dict[str, Any]:
        return Schema().boolean().build()

    @staticmethod
    def array(items: dict[str, Any] | None = None) -> dict[str, Any]:
        return Schema().array(items).build()

    @staticmethod
    def object(properties: dict[str, Any] | None = None) -> dict[str, Any]:
        return Schema().object(properties).build()

    @staticmethod
    def from_field(field: Any) -> dict[str, Any]:
        schema = Schema()
        field_type = type(field).__name__.lower()

        if field_type == "strfield":
            schema.string()
            if getattr(field, "min_length", None) is not None:
                schema.min_length(field.min_length)
            if getattr(field, "max_length", None) is not None:
                schema.max_length(field.max_length)

        elif field_type == "intfield":
            schema.integer()
            if getattr(field, "minimum", None) is not None:
                schema.minimum(field.minimum)
            if getattr(field, "maximum", None) is not None:
                schema.maximum(field.maximum)

        elif field_type == "floatfield":
            schema.number()
            if getattr(field, "minimum", None) is not None:
                schema.minimum(field.minimum)
            if getattr(field, "maximum", None) is not None:
                schema.maximum(field.maximum)

        elif field_type == "boolfield":
            schema.boolean()

        elif field_type == "emailfield":
            schema.string().format("email")

        elif field_type == "choicefield":
            if hasattr(field, "choices"):
                choices = list(field.choices)
                if choices:
                    first_type = type(choices[0])
                    if first_type is int:
                        schema.integer()
                    elif first_type is float:
                        schema.number()
                    elif first_type is bool:
                        schema.boolean()
                    else:
                        schema.string()
                    schema.enum(*choices)

        elif field_type == "datefield":
            schema.string().format("date")

        elif field_type == "datetimefield":
            schema.string().format("date-time")

        elif field_type == "decimalfield":
            schema.number()
            if getattr(field, "minimum", None) is not None:
                schema.minimum(field.minimum)
            if getattr(field, "maximum", None) is not None:
                schema.maximum(field.maximum)

        elif field_type == "uuidfield":
            schema.string().format("uuid")

        elif field_type == "listfield":
            item_field = getattr(field, "item_field", None)
            schema.array(SchemaBuilder.from_field(item_field) if item_field is not None else {})
            if getattr(field, "min_items", None) is not None:
                schema._schema["minItems"] = field.min_items
            if getattr(field, "max_items", None) is not None:
                schema._schema["maxItems"] = field.max_items

        elif field_type == "nestedfield":
            nested = getattr(field, "schema_class", None)
            if nested is not None:
                properties = {
                    name: SchemaBuilder.from_field(child)
                    for name, child in getattr(nested, "__fields__", {}).items()
                }
                schema.object(properties)
                required = [
                    name for name, child in getattr(nested, "__fields__", {}).items()
                    if getattr(child, "required", False)
                ]
                if required:
                    schema.required(*required)

        if hasattr(field, "required") and field.required:
            pass

        return schema.build()
