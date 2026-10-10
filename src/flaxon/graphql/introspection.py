from __future__ import annotations

from typing import Any


class Introspection:
    """Introspection implementation for the graphql subsystem."""

    @staticmethod
    def get_introspection_query(schema: Any) -> dict[str, Any]:
        """Return the introspection query."""
        return {
            "__schema": {
                "queryType": {"name": schema.query.name if schema.query else None},
                "mutationType": {"name": schema.mutation.name if schema.mutation else None},
                "subscriptionType": {"name": schema.subscription.name if schema.subscription else None},
                "types": Introspection._get_types(schema),
                "directives": Introspection._get_directives(schema),
            }
        }

    @staticmethod
    def _get_types(schema: Any) -> list[dict[str, Any]]:
        types = []
        for _type_name, type_obj in schema.get_types().items():
            types.append(Introspection._get_type_info(type_obj))
        return types

    @staticmethod
    def _get_type_info(type_obj: Any) -> dict[str, Any]:
        return {
            "kind": "OBJECT",
            "name": type_obj.name,
            "description": getattr(type_obj, "description", None),
            "fields": Introspection._get_fields(type_obj),
            "interfaces": [],
            "enumValues": None,
            "possibleTypes": None,
        }

    @staticmethod
    def _get_fields(type_obj: Any) -> list[dict[str, Any]]:
        fields = []
        for field_name, field in type_obj.fields.items():
            field_info = {
                "name": field_name,
                "description": getattr(field, "description", None),
                "type": Introspection._get_type_ref(field.type),
                "args": Introspection._get_args(field.args),
            }
            fields.append(field_info)
        return fields

    @staticmethod
    def _get_type_ref(type_obj: Any) -> dict[str, Any]:
        if hasattr(type_obj, "type"):
            return {
                "kind": "NON_NULL",
                "ofType": Introspection._get_type_ref(type_obj.type),
            }
        if hasattr(type_obj, "__origin__"):
            return {
                "kind": "LIST",
                "ofType": Introspection._get_type_ref(type_obj.__args__[0]),
            }
        return {
            "kind": "OBJECT",
            "name": type_obj.name if hasattr(type_obj, "name") else str(type_obj),
        }

    @staticmethod
    def _get_args(args: dict[str, Any]) -> list[dict[str, Any]]:
        result = []
        for arg_name, arg_info in args.items():
            result.append({
                "name": arg_name,
                "description": arg_info.get("description"),
                "type": Introspection._get_type_ref(arg_info.get("type")),
                "defaultValue": arg_info.get("default"),
            })
        return result

    @staticmethod
    def _get_directives(schema: Any) -> list[dict[str, Any]]:
        directives = []
        for directive in schema.get_directives():
            directives.append({
                "name": directive.name,
                "description": directive.description,
                "locations": directive.locations,
                "args": Introspection._get_args(directive.args),
            })
        return directives
