"""
Middleware stack management for Flaxon.

This module provides utilities for building and managing middleware stacks.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class MiddlewareStack:
    """
    Middleware stack builder.

    This class manages a stack of middleware and builds the final
    ASGI application.

    Example:
        ```python
        stack = MiddlewareStack()
        stack.add(CORSMiddleware, allowed_origins=["[https://example.com](https://example.com)"])
        stack.add(RequestIDMiddleware)
        stack.add(CompressionMiddleware)

        app = stack.build(base_app)
        ```
    """

    def __init__(self) -> None:
        """Initialize the middleware stack."""
        self._middleware: list[tuple[type[Any], dict[str, Any]]] = []

    def add(self, middleware_class: type[Any], **options: Any) -> None:
        """
        Add middleware to the stack.

        Args:
            middleware_class: The middleware class to add.
            **options: Options to pass to the middleware constructor.
        """
        self._middleware.append((middleware_class, options))

    def remove(self, middleware_class: type[Any]) -> None:
        """
        Remove middleware from the stack.

        Args:
            middleware_class: The middleware class to remove.
        """
        self._middleware = [(cls, opts) for cls, opts in self._middleware if cls != middleware_class]

    def clear(self) -> None:
        """Clear all middleware from the stack."""
        self._middleware.clear()

    def build(self, app: Any) -> Any:
        """
        Build the middleware stack.

        Args:
            app: The base ASGI application.

        Returns:
            The wrapped ASGI application.
        """
        for middleware_class, options in reversed(self._middleware):
            app = middleware_class(app, **options)
        return app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """
        Call the middleware stack.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        raise RuntimeError("MiddlewareStack must be built before calling. Use build() first.")

    def __len__(self) -> int:
        """Get the number of middleware in the stack."""
        return len(self._middleware)

    def __iter__(self) -> Any:
        """Iterate over the middleware stack."""
        return iter(self._middleware)

    def __repr__(self) -> str:
        """Get a string representation of the middleware stack."""
        names = [cls.__name__ for cls, _ in self._middleware]
        return f"MiddlewareStack({', '.join(names)})"


class MiddlewareChain:
    """
    Chain of middleware for sequential processing.

    This class chains middleware together so they execute in order.
    """

    def __init__(self, app: Any) -> None:
        """
        Initialize the middleware chain.

        Args:
            app: The base ASGI application.
        """
        self.app = app
        self._middleware: list[Callable] = []

    def add(self, middleware: Callable) -> None:
        """
        Add middleware to the chain.

        Args:
            middleware: A middleware callable.
        """
        self._middleware.append(middleware)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """
        Execute the middleware chain.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if not self._middleware:
            await self.app(scope, receive, send)
            return

        current = self.app

        for middleware in reversed(self._middleware):
            current = middleware(current)

        await current(scope, receive, send)

    def __len__(self) -> int:
        """Get the number of middleware in the chain."""
        return len(self._middleware)

    def __repr__(self) -> str:
        """Get a string representation of the middleware chain."""
        names = [str(m) for m in self._middleware]
        return f"MiddlewareChain({', '.join(names)})"
