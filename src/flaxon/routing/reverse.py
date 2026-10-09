"""
URL reverse resolution for Flaxon.

This module provides URL generation from route names and parameters.
"""

from __future__ import annotations

import re
from typing import Any

from flaxon.exceptions import NotFound


class ReverseResolver:
    """
    Resolves URLs from route names and parameters.

    Example:
        ```python
        resolver = ReverseResolver(router)


        @app.get("/users/<int:user_id>", name="users.detail")
        async def get_user(user_id: int):
            return {"id": user_id}


        url = resolver.reverse("users.detail", user_id=42)
        # url == "/users/42"
        ```
    """

    def __init__(self, router: Any) -> None:
        """
        Initialize the reverse resolver.

        Args:
            router: The router to resolve URLs from.
        """
        self.router = router

    def reverse(self, name: str, **params: Any) -> str:
        """
        Generate a URL for a named route.

        Args:
            name: The route name.
            **params: Path parameters.

        Returns:
            The generated URL.

        Raises:
            NotFound: If the route name is not found.
            ValueError: If parameters are missing or invalid.
        """
        routes = getattr(self.router, "routes", [])
        websocket_routes = getattr(self.router, "websocket_routes", [])

        for route in [*routes, *websocket_routes]:
            if getattr(route, "name", None) != name:
                continue

            path = route.path

            # Extract all parameter names from the path
            param_names = self._extract_params(path)

            # Check if all parameters are provided
            for param_name in param_names:
                if param_name not in params:
                    raise ValueError(f"Missing parameter '{param_name}' for route '{name}'")

            # Replace parameters with values
            for key, value in params.items():
                if key in param_names:
                    path = self._replace_param(path, key, str(value))

            return path

        raise NotFound(f"Route '{name}' not found")

    def _extract_params(self, path: str) -> list[str]:
        """Extract parameter names from a path."""
        params = []

        # Flask-style: <name> or <type:name>
        for match in re.finditer(r"<(?:[a-zA-Z_][a-zA-Z0-9_]*:)?([a-zA-Z_][a-zA-Z0-9_]*)>", path):
            params.append(match.group(1))

        # Brace-style: {name} or {name:type}
        for match in re.finditer(r"{([a-zA-Z_][a-zA-Z0-9_]*)(?::[a-zA-Z_][a-zA-Z0-9_]*)?}", path):
            params.append(match.group(1))

        return params

    def _replace_param(self, path: str, name: str, value: str) -> str:
        """Replace a parameter in a path with its value."""
        path = re.sub(rf"<(?:[a-zA-Z_][a-zA-Z0-9_]*:)?{re.escape(name)}>", value, path)
        path = re.sub(rf"{{{re.escape(name)}(?::[a-zA-Z_][a-zA-Z0-9_]*)?}}", value, path)
        return path

    def url_for(self, name: str, **params: Any) -> str:
        """
        Alias for reverse().

        Args:
            name: The route name.
            **params: Path parameters.

        Returns:
            The generated URL.
        """
        return self.reverse(name, **params)

    def has_route(self, name: str) -> bool:
        """
        Check if a route with the given name exists.

        Args:
            name: The route name.

        Returns:
            True if the route exists, False otherwise.
        """
        routes = getattr(self.router, "routes", [])
        websocket_routes = getattr(self.router, "websocket_routes", [])

        for route in [*routes, *websocket_routes]:
            if getattr(route, "name", None) == name:
                return True

        return False
