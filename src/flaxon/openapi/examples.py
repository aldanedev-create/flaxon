from __future__ import annotations

from typing import Any


class Example:
    """Example implementation for the openapi subsystem."""

    def __init__(self, summary: str | None = None, value: Any = None) -> None:
        self.summary = summary
        self.value = value

    def build(self) -> dict[str, Any]:
        """Perform the build operation for example."""
        result = {}
        if self.summary:
            result["summary"] = self.summary
        if self.value is not None:
            result["value"] = self.value
        return result


class Examples:
    """Examples implementation for the openapi subsystem."""

    @staticmethod
    def user_create() -> dict[str, Any]:
        """Perform the user create operation for examples."""
        return {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
        }

    @staticmethod
    def user_response() -> dict[str, Any]:
        """Perform the user response operation for examples."""
        return {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "created_at": "2024-01-01T00:00:00Z",
        }

    @staticmethod
    def users_response() -> list[dict[str, Any]]:
        """Perform the users response operation for examples."""
        return [
            {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30,
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": 2,
                "name": "Jane Doe",
                "email": "jane@example.com",
                "age": 25,
                "created_at": "2024-01-02T00:00:00Z",
            },
        ]

    @staticmethod
    def error_response() -> dict[str, Any]:
        """Perform the error response operation for examples."""
        return {
            "success": False,
            "error": {
                "code": "FX-VAL-001",
                "message": "Validation failed",
                "fields": {
                    "email": ["Enter a valid email address."],
                },
            },
        }

    @staticmethod
    def paginated_response() -> dict[str, Any]:
        """Perform the paginated response operation for examples."""
        return {
            "success": True,
            "data": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
            ],
            "pagination": {
                "page": 1,
                "per_page": 20,
                "total": 100,
                "total_pages": 5,
                "has_next": True,
                "has_prev": False,
            },
        }

    @staticmethod
    def health_check() -> dict[str, Any]:
        """Report the current health of the configured resource."""
        return {
            "success": True,
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00Z",
        }

    @staticmethod
    def get_example(name: str) -> dict[str, Any] | None:
        """Return the example."""
        examples = {
            "user_create": Examples.user_create(),
            "user_response": Examples.user_response(),
            "users_response": Examples.users_response(),
            "error_response": Examples.error_response(),
            "paginated_response": Examples.paginated_response(),
            "health_check": Examples.health_check(),
        }
        return examples.get(name)
