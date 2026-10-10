from __future__ import annotations

from typing import Any

from flaxon.exceptions import FlaxonError


class GraphQLError(FlaxonError):
    """Report a graph qlerror failure."""

    def __init__(
        self, message: str, locations: list[dict[str, int]] | None = None, path: list[str | int] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.locations = locations or []
        self.path = path or []

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        result = {"message": self.message}
        if self.locations:
            result["locations"] = self.locations
        if self.path:
            result["path"] = self.path
        return result


class GraphQLSyntaxError(GraphQLError):
    """Report a graph qlsyntax failure."""

    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(message)
        self.line = line
        self.column = column
        self.locations = [{"line": line, "column": column}]


class GraphQLValidationError(GraphQLError):
    """Report a graph qlvalidation failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class GraphQLExecutionError(GraphQLError):
    """Report a graph qlexecution failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class GraphQLTypeError(GraphQLError):
    """Report a graph qltype failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
