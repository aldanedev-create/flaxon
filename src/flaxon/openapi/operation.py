from __future__ import annotations

from typing import Any


class Operation:
    """Operation implementation for the openapi subsystem."""

    def __init__(self, path: str, method: str) -> None:
        self.path = path
        self.method = method.lower()
        self._operation: dict[str, Any] = {
            "responses": {
                "200": {"description": "Successful response"},
                "400": {"description": "Bad request"},
                "401": {"description": "Unauthorized"},
                "403": {"description": "Forbidden"},
                "404": {"description": "Not found"},
                "500": {"description": "Internal server error"},
            }
        }

    def summary(self, summary: str) -> Operation:
        """Perform the summary operation for operation."""
        self._operation["summary"] = summary
        return self

    def description(self, description: str) -> Operation:
        """Perform the description operation for operation."""
        self._operation["description"] = description
        return self

    def operation_id(self, operation_id: str) -> Operation:
        """Perform the operation id operation for operation."""
        self._operation["operationId"] = operation_id
        return self

    def tags(self, *tags: str) -> Operation:
        """Perform the tags operation for operation."""
        self._operation["tags"] = list(tags)
        return self

    def parameters(self, *parameters: dict[str, Any]) -> Operation:
        """Perform the parameters operation for operation."""
        self._operation["parameters"] = list(parameters)
        return self

    def request_body(self, content: dict[str, Any]) -> Operation:
        """Request the body."""
        self._operation["requestBody"] = {
            "content": content,
        }
        return self

    def responses(self, responses: dict[str, dict[str, Any]]) -> Operation:
        """Perform the responses operation for operation."""
        self._operation["responses"] = responses
        return self

    def security(self, security: list[dict[str, list[str]]]) -> Operation:
        """Perform the security operation for operation."""
        self._operation["security"] = security
        return self

    def deprecated(self, deprecated: bool = True) -> Operation:
        """Perform the deprecated operation for operation."""
        self._operation["deprecated"] = deprecated
        return self

    def build(self) -> dict[str, Any]:
        """Perform the build operation for operation."""
        return self._operation


class OperationBuilder:
    """Operation builder implementation for the openapi subsystem."""

    def __init__(self, path: str, method: str) -> None:
        """Perform the   init   operation for operation builder."""
        self.operation = Operation(path, method)

    def build(self) -> dict[str, Any]:
        """Perform the build operation for operation builder."""
        return self.operation.build()

    def with_summary(self, summary: str) -> OperationBuilder:
        """Configure the summary."""
        self.operation.summary(summary)
        return self

    def with_description(self, description: str) -> OperationBuilder:
        """Configure the description."""
        self.operation.description(description)
        return self

    def with_tags(self, *tags: str) -> OperationBuilder:
        """Configure the tags."""
        self.operation.tags(*tags)
        return self

    def with_parameters(self, *parameters: dict[str, Any]) -> OperationBuilder:
        """Configure the parameters."""
        self.operation.parameters(*parameters)
        return self

    def with_json_request(self, schema: dict[str, Any]) -> OperationBuilder:
        """Configure the json request."""
        self.operation.request_body({"application/json": {"schema": schema}})
        return self

    def with_json_response(
        self, status: int, schema: dict[str, Any], description: str = "Successful response"
    ) -> OperationBuilder:
        """Configure the json response."""
        self.operation.responses({
            str(status): {
                "description": description,
                "content": {"application/json": {"schema": schema}},
            }
        })
        return self

    def with_path_parameter(
        self, name: str, schema_type: str = "string", description: str = "", required: bool = True
    ) -> OperationBuilder:
        """Configure the path parameter."""
        param = {
            "name": name,
            "in": "path",
            "required": required,
            "schema": {"type": schema_type},
        }
        if description:
            param["description"] = description

        params = self.operation._operation.get("parameters", [])
        params.append(param)
        self.operation.parameters(*params)
        return self

    def with_query_parameter(
        self, name: str, schema_type: str = "string", description: str = "", required: bool = False
    ) -> OperationBuilder:
        """Configure the query parameter."""
        param = {
            "name": name,
            "in": "query",
            "required": required,
            "schema": {"type": schema_type},
        }
        if description:
            param["description"] = description

        params = self.operation._operation.get("parameters", [])
        params.append(param)
        self.operation.parameters(*params)
        return self

    def with_auth(self) -> OperationBuilder:
        """Configure the auth."""
        self.operation.security([{"bearerAuth": []}])
        return self
