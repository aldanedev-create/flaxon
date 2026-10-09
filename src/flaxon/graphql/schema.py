from __future__ import annotations

from typing import Any

from .directives import Directive, include_directive, skip_directive
from .exceptions import GraphQLError
from .executor import execute
from .introspection import Introspection
from .resolver import Resolver
from .types import ObjectType
from .validation import validate_query


class GraphQLSchema:
    def __init__(
        self,
        query: ObjectType | None = None,
        mutation: ObjectType | None = None,
        subscription: ObjectType | None = None,
    ) -> None:
        self.query = query
        self.mutation = mutation
        self.subscription = subscription
        self._types: dict[str, ObjectType] = {}
        self._directives: list[Directive] = [skip_directive, include_directive]
        self._resolver = Resolver()

        if query:
            self._types[query.name] = query

        if mutation:
            self._types[mutation.name] = mutation

        if subscription:
            self._types[subscription.name] = subscription

    def add_type(self, type_obj: ObjectType) -> None:
        self._types[type_obj.name] = type_obj

    def get_type(self, name: str) -> ObjectType | None:
        return self._types.get(name)

    def get_types(self) -> dict[str, ObjectType]:
        return self._types

    def add_directive(self, directive: Directive) -> None:
        self._directives.append(directive)

    def get_directives(self) -> list[Directive]:
        return self._directives

    def resolver(self) -> Resolver:
        return self._resolver

    async def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        context: Any = None,
        operation_name: str | None = None,
    ) -> dict[str, Any]:
        try:
            from .parser import parse

            document = parse(query)

            errors = validate_query(self, document)
            if errors:
                return {"errors": [{"message": str(e)} for e in errors]}

            result = await execute(
                schema=self,
                document=document,
                context=context,
                variables=variables or {},
                operation_name=operation_name,
            )

            return result

        except GraphQLError as exc:
            return {"errors": [{"message": str(exc)}]}
        except Exception as exc:
            return {"errors": [{"message": f"Internal server error: {exc}"}]}

    async def introspection(self) -> dict[str, Any]:
        return Introspection.get_introspection_query(self)
