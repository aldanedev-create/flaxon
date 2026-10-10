from __future__ import annotations

import json
from typing import Any

from flaxon._imports import import_attribute


class GraphQLMiddleware:
    """Graph qlmiddleware implementation for the graphql subsystem."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self._middleware: list[Any] = []

    def add(self, middleware: Any) -> None:
        """Add the supplied item to this collection."""
        self._middleware.append(middleware)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")

        if path != "/graphql":
            await self.app(scope, receive, send)
            return

        request = None
        request_type = import_attribute("flaxon.http", "Request")

        request = request_type(scope, receive, None)

        if request.method == "GET":
            await self._handle_get(request, scope, receive, send)
        elif request.method == "POST":
            await self._handle_post(request, scope, receive, send)
        else:
            await self._send_error(405, "Method not allowed", scope, send)

    async def _handle_get(self, request: Any, scope: dict[str, Any], receive: Any, send: Any) -> None:
        query = request.query.get("query", "")
        variables = request.query.get("variables", "{}")

        try:
            variables = json.loads(variables)
        except json.JSONDecodeError:
            variables = {}

        await self._execute_query(query, variables, request, scope, send)

    async def _handle_post(self, request: Any, scope: dict[str, Any], receive: Any, send: Any) -> None:
        data = await request.json()
        query = data.get("query", "")
        variables = data.get("variables", {})

        await self._execute_query(query, variables, request, scope, send)

    async def _execute_query(
        self, query: str, variables: dict[str, Any], request: Any, scope: dict[str, Any], send: Any
    ) -> None:
        graphql_schema = getattr(scope.get("app"), "_graphql_schema", None)

        if graphql_schema is None:
            await self._send_error(500, "GraphQL schema not configured", scope, send)
            return

        context = {"request": request, "scope": scope}

        for middleware in self._middleware:
            if hasattr(middleware, "before"):
                await middleware.before(context)

        result = await graphql_schema.execute(query, variables, context)

        for middleware in self._middleware:
            if hasattr(middleware, "after"):
                await middleware.after(context, result)

        await self._send_response(result, scope, send)

    async def _send_response(self, data: dict[str, Any], scope: dict[str, Any], send: Any) -> None:

        body = json.dumps(data).encode("utf-8")

        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("latin-1")),
            ],
        })

        await send({
            "type": "http.response.body",
            "body": body,
            "more_body": False,
        })

    async def _send_error(self, status: int, message: str, scope: dict[str, Any], send: Any) -> None:

        body = json.dumps({"errors": [{"message": message}]}).encode("utf-8")

        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("latin-1")),
            ],
        })

        await send({
            "type": "http.response.body",
            "body": body,
            "more_body": False,
        })
