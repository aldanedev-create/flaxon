from __future__ import annotations

from typing import Any


class Resolver:
    """Resolver implementation for the graphql subsystem."""

    def __init__(self) -> None:
        self._resolvers: dict[str, Any] = {}
        self._default_resolver = self._default_resolve

    def register(self, type_name: str, field_name: str, resolver: Any) -> None:
        """Perform the register operation for resolver."""
        key = f"{type_name}.{field_name}"
        self._resolvers[key] = resolver

    def register_type_resolver(self, type_name: str, resolver: Any) -> None:
        """Register the type resolver."""
        self._resolvers[f"{type_name}"] = resolver

    def get(self, type_name: str, field_name: str) -> Any:
        """Retrieve the requested value using this object's configured behavior."""
        key = f"{type_name}.{field_name}"
        return self._resolvers.get(key, self._default_resolver)

    def get_type_resolver(self, type_name: str) -> Any:
        """Return the type resolver."""
        return self._resolvers.get(type_name)

    def _default_resolve(self, parent: Any, args: dict[str, Any], context: Any, info: Any) -> Any:
        if parent is None:
            return None

        field_name = info.field_name

        if isinstance(parent, dict):
            return parent.get(field_name)

        if hasattr(parent, field_name):
            attr = getattr(parent, field_name)
            if callable(attr):
                return attr()
            return attr

        return None

    async def resolve(  # noqa: PLR0917 - preserve existing positional API
        self, type_name: str, field_name: str, parent: Any, args: dict[str, Any], context: Any, info: Any
    ) -> Any:
        """Perform the resolve operation for resolver."""
        resolver = self.get(type_name, field_name)

        if resolver is not None and resolver != self._default_resolver and callable(resolver):
            result = resolver(parent, args, context, info)
            if hasattr(result, "__await__"):
                return await result
            return result

        return self._default_resolver(parent, args, context, info)
