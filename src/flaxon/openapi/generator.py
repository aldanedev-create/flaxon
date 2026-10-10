"""Automatic OpenAPI 3.1 generation for Flaxon routes."""

from __future__ import annotations

import inspect
import re
import types
import typing
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from flaxon._imports import import_attribute
from flaxon.routing import MISSING, Query
from flaxon.routing.execution import is_scalar_query

from .operation import OperationBuilder
from .schema import SchemaBuilder

_PARAMETER = re.compile(r"<(?:(?P<converter>[a-zA-Z_][a-zA-Z0-9_]*):)?(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)>")


class OpenAPIGenerator:
    """Build an OpenAPI document from a Flaxon application's route registry."""

    def __init__(
        self,
        title: str = "Flaxon API",
        version: str = "1.0.0",
        description: str | None = None,
    ) -> None:
        self.title = title
        self.version = version
        self._paths: dict[str, dict[str, Any]] = {}
        self._schemas: dict[str, Any] = {}
        self._tags: list[dict[str, str]] = []
        self._security: list[dict[str, list[str]]] = []
        self._info: dict[str, Any] = {"title": title, "version": version}
        if description:
            self._info["description"] = description
        self._servers: list[dict[str, str]] = []

    def add_path(self, path: str, method: str, operation: dict[str, Any]) -> None:
        """Add the path."""
        self._paths.setdefault(path, {})[method.lower()] = operation

    def add_schema(self, name: str, schema: dict[str, Any]) -> None:
        """Add the schema."""
        self._schemas[name] = schema

    def add_tag(self, name: str, description: str | None = None) -> None:
        """Add the tag."""
        tag = {"name": name}
        if description:
            tag["description"] = description
        if tag not in self._tags:
            self._tags.append(tag)

    def add_server(self, url: str, description: str | None = None) -> None:
        """Add the server."""
        server = {"url": url}
        if description:
            server["description"] = description
        self._servers.append(server)

    def add_security(self, scheme: str, scopes: list[str] | None = None) -> None:
        """Add the security."""
        self._security.append({scheme: scopes or []})

    def add_info(self, key: str, value: Any) -> None:
        """Add the info."""
        self._info[key] = value

    def generate(self) -> dict[str, Any]:
        """Perform the generate operation for open apigenerator."""
        document: dict[str, Any] = {
            "openapi": "3.1.0",
            "info": self._info,
            "paths": self._paths,
            "components": {"schemas": self._schemas},
        }
        if self._servers:
            document["servers"] = self._servers
        if self._tags:
            document["tags"] = self._tags
        if self._security:
            document["security"] = self._security
        return document

    def generate_from_app(self, app: Any, include_internal: bool = False) -> dict[str, Any]:
        """Generate a fresh document from the current application routes."""
        for route in app.router.routes:
            if not include_internal and (route.name or "").startswith("flaxon_"):
                continue
            self._generate_route(route)
        return self.generate()

    def _generate_route(self, route: Any) -> None:
        endpoint = route.endpoint
        openapi_path = _openapi_path(route.path)
        docstring = inspect.getdoc(endpoint) or ""
        doc_lines = docstring.splitlines()
        summary = route.summary or (doc_lines[0].strip() if doc_lines else "")
        description = route.description or "\n".join(line for line in doc_lines[1:] if line.strip()).strip()
        try:
            hints = typing.get_type_hints(endpoint)
        except (NameError, TypeError, AttributeError):
            hints = getattr(endpoint, "__annotations__", {}) or {}
        signature = inspect.signature(endpoint)
        body_schema = self._find_body_schema(signature, hints, route)

        for method in sorted(route.methods):
            builder = OperationBuilder(openapi_path, method.lower())
            operation = builder.build()
            self._apply_route_metadata(operation, route, summary=summary, description=description)
            parameters = self._route_parameters(route, signature, hints)
            if parameters:
                operation["parameters"] = parameters

            if body_schema is not None and method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
                operation["requestBody"] = {
                    "required": True,
                    "content": {"application/json": {"schema": body_schema}},
                }

            return_annotation = hints.get("return", signature.return_annotation)
            response_schema = self._schema_for_annotation(return_annotation)
            if response_schema and response_schema != {}:
                success = operation["responses"].setdefault("200", {"description": "Successful response"})
                success["content"] = {"application/json": {"schema": response_schema}}

            self._apply_responses(operation, getattr(route, "responses", None))
            self.add_path(openapi_path, method, operation)

    @staticmethod
    def _apply_route_metadata(operation, route, *, summary, description):
        if summary:
            operation["summary"] = summary
        if description:
            operation["description"] = description
        if route.operation_id:
            operation["operationId"] = route.operation_id
        elif route.name:
            operation["operationId"] = route.name
        if route.tags:
            operation["tags"] = list(route.tags)
        if route.deprecated:
            operation["deprecated"] = True
        if route.security is not None:
            operation["security"] = route.security

    def _route_parameters(self, route, signature, hints):

        parameters: list[dict[str, Any]] = []
        converter_types = {
            "int": "integer",
            "float": "number",
            "str": "string",
            "path": "string",
            "uuid": "string",
        }
        for name, converter_name in getattr(route, "parameters", []):
            parameter: dict[str, Any] = {
                "name": name,
                "in": "path",
                "required": True,
                "schema": {"type": converter_types.get(converter_name, "string")},
            }
            if converter_name == "uuid":
                parameter["schema"]["format"] = "uuid"
            parameters.append(parameter)

        for name, parameter in signature.parameters.items():
            declaration = parameter.default
            annotation = hints.get(name, parameter.annotation)
            if not isinstance(declaration, Query):
                path_names = {item[0] for item in getattr(route, "parameters", [])}
                if (
                    name in path_names
                    or name in {"request", "socket", "websocket"}
                    or not is_scalar_query(annotation)
                ):
                    continue
                default = MISSING if parameter.default is inspect.Parameter.empty else parameter.default
                declaration = Query(default=default)
            query_schema = self._schema_for_annotation(hints.get(name, parameter.annotation))
            if query_schema == {}:
                query_schema = {"type": "string"}
            self._apply_query_constraints(query_schema, declaration)
            item: dict[str, Any] = {
                "name": declaration.alias or name,
                "in": "query",
                "required": declaration.default is MISSING,
                "schema": query_schema,
            }
            if declaration.description:
                item["description"] = declaration.description
            if declaration.deprecated:
                item["deprecated"] = True
            parameters.append(item)
        return parameters

    @staticmethod
    def _apply_query_constraints(query_schema, declaration):
        if declaration.default is not MISSING:
            query_schema["default"] = declaration.default
        if declaration.ge is not None:
            query_schema["minimum"] = declaration.ge
        if declaration.le is not None:
            query_schema["maximum"] = declaration.le
        if declaration.min_length is not None:
            query_schema["minLength"] = declaration.min_length
        if declaration.max_length is not None:
            query_schema["maxLength"] = declaration.max_length

    def _find_body_schema(
        self, signature: inspect.Signature, hints: dict[str, Any], route: Any
    ) -> dict[str, Any] | None:
        path_names = {name for name, _ in getattr(route, "parameters", [])}
        for name, parameter in signature.parameters.items():
            if name in path_names or name in {"request", "socket", "websocket"}:
                continue
            if isinstance(parameter.default, Query):
                continue
            annotation = hints.get(name, parameter.annotation)
            schema = self._schema_for_annotation(annotation)
            if schema and self._is_model_annotation(annotation):
                return schema
        return None

    def _is_model_annotation(self, annotation: Any) -> bool:
        if not isinstance(annotation, type):
            return False
        try:
            schema_type = import_attribute("flaxon.validation", "Schema")

            if issubclass(annotation, schema_type):
                return True
        except (ImportError, TypeError):
            pass
        try:
            is_pydantic_model_type = import_attribute(
                "flaxon.integrations.pydantic", "is_pydantic_model_type"
            )

            return is_pydantic_model_type(annotation)
        except ImportError:
            return False

    def _schema_for_annotation(self, annotation: Any) -> dict[str, Any]:
        if annotation is inspect.Parameter.empty or annotation is None or annotation is type(None):
            return {}
        if isinstance(annotation, str):
            return {"type": "string"}
        origin = typing.get_origin(annotation)
        if origin is not None:
            return self._generic_annotation_schema(origin, typing.get_args(annotation))
        if not isinstance(annotation, type):
            return {}
        schemas = {
            list: {"type": "array", "items": {}},
            tuple: {"type": "array", "items": {}},
            set: {"type": "array", "items": {}},
            frozenset: {"type": "array", "items": {}},
            dict: {"type": "object", "additionalProperties": {}},
            bool: {"type": "boolean"},
            int: {"type": "integer"},
            float: {"type": "number"},
            str: {"type": "string"},
            date: {"type": "string", "format": "date"},
            datetime: {"type": "string", "format": "date-time"},
            Decimal: {"type": "number"},
            UUID: {"type": "string", "format": "uuid"},
        }
        return schemas[annotation] if annotation in schemas else self._registered_model_schema(annotation)

    def _generic_annotation_schema(self, origin: Any, args: tuple[Any, ...]) -> dict[str, Any]:
        if origin is typing.Annotated:
            return self._schema_for_annotation(args[0])
        if origin in (typing.Union, types.UnionType):
            return self._union_annotation_schema(args)
        if origin in (list, tuple, set, frozenset):
            return {"type": "array", "items": self._schema_for_annotation(args[0]) if args else {}}
        if origin is dict:
            return {
                "type": "object",
                "additionalProperties": self._schema_for_annotation(args[1]) if len(args) > 1 else {},
            }
        if origin is typing.Literal:
            values = list(args)
            schema = self._schema_for_annotation(type(values[0])) if values else {"type": "string"}
            schema["enum"] = values
            return schema
        return {}

    def _union_annotation_schema(self, args: tuple[Any, ...]) -> dict[str, Any]:
        non_null = [item for item in args if item is not type(None)]
        schema = self._schema_for_annotation(non_null[0]) if non_null else {}
        if len(non_null) == 1 and len(non_null) != len(args):
            schema = dict(schema)
            schema["nullable"] = True
        return schema

    def _registered_model_schema(self, annotation: type[Any]) -> dict[str, Any]:
        native = self._native_model_schema(annotation)
        if native is not None:
            name = annotation.__name__
            self._schemas[name] = native
            return {"$ref": f"#/components/schemas/{name}"}
        pydantic = self._pydantic_model_schema(annotation)
        if pydantic is not None:
            name, schema = pydantic
            self._schemas[name] = schema
            return {"$ref": f"#/components/schemas/{name}"}
        return {}

    def _native_model_schema(self, model: type[Any]) -> dict[str, Any] | None:
        try:
            schema_type = import_attribute("flaxon.validation", "Schema")

            if not issubclass(model, schema_type):
                return None
        except (ImportError, TypeError):
            return None
        properties: dict[str, Any] = {}
        required: list[str] = []
        for name, field in getattr(model, "__fields__", {}).items():
            properties[name] = SchemaBuilder.from_field(field)
            if getattr(field, "description", None):
                properties[name]["description"] = field.description
            if getattr(field, "examples", None):
                properties[name]["examples"] = list(field.examples)
            if getattr(field, "default", MISSING) is not None and not getattr(field, "required", False):
                properties[name]["default"] = field.default
            if getattr(field, "nullable", False):
                properties[name]["nullable"] = True
            if getattr(field, "required", False):
                required.append(name)
        schema: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema

    def _pydantic_model_schema(self, model: type[Any]) -> tuple[str, dict[str, Any]] | None:
        try:
            is_pydantic_model_type = import_attribute(
                "flaxon.integrations.pydantic", "is_pydantic_model_type"
            )

            if not is_pydantic_model_type(model):
                return None
        except ImportError:
            return None
        exporter = getattr(model, "model_json_schema", None) or getattr(model, "schema", None)
        if not callable(exporter):
            return None
        raw = exporter()
        definitions = raw.pop("$defs", raw.pop("definitions", {}))
        for name, schema in definitions.items():
            self._schemas[name] = _replace_definition_refs(schema)
        name = getattr(model, "__name__", "Model")
        return name, _replace_definition_refs(raw)

    def _apply_responses(self, operation: dict[str, Any], configured: dict[str | int, Any] | None) -> None:
        if not configured:
            return
        responses = operation.setdefault("responses", {})
        for status, raw_value in configured.items():
            value = raw_value
            key = str(status)
            if isinstance(value, str):
                responses[key] = {"description": value}
                continue
            if isinstance(value, tuple) and len(value) == 2:
                schema, description = value
                schema = self._schema_for_annotation(schema) if isinstance(schema, type) else schema
                responses[key] = {
                    "description": str(description),
                    "content": {"application/json": {"schema": schema}},
                }
                continue
            if isinstance(value, dict) and any(
                item in value for item in ("description", "content", "$ref", "headers")
            ):
                responses[key] = value
                continue
            if isinstance(value, type):
                value = self._schema_for_annotation(value)
            responses[key] = {
                "description": "Response",
                "content": {"application/json": {"schema": value}},
            }


def _openapi_path(path: str) -> str:
    return _PARAMETER.sub(lambda match: "{" + match.group("name") + "}", path)


def _replace_definition_refs(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _replace_definition_refs(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_definition_refs(item) for item in value]
    if isinstance(value, str) and value.startswith("#/$defs/"):
        return value.replace("#/$defs/", "#/components/schemas/", 1)
    if isinstance(value, str) and value.startswith("#/definitions/"):
        return value.replace("#/definitions/", "#/components/schemas/", 1)
    return value


def generate_openapi(app: Any, title: str = "Flaxon API", version: str = "1.0.0") -> dict[str, Any]:
    """Generate the openapi."""
    return OpenAPIGenerator(title, version).generate_from_app(app)
