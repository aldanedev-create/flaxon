from __future__ import annotations

from typing import Any


class Assertions:
    """Assertions implementation for the testing subsystem."""

    @staticmethod
    def assert_status(response: Any, expected: int) -> None:
        # FIX (S101): Ruff warning for assert statements in non-test helper code
        # If this is part of testing utilities,
        """Assert the status."""
        assert response.status_code == expected, f"Expected status {expected}, got {response.status_code}"

    @staticmethod
    def assert_json(response: Any) -> dict[str, Any]:
        """Assert the json."""
        data = response.json()
        assert isinstance(data, dict), f"Expected JSON object, got {type(data)}"
        return data

    @staticmethod
    def assert_json_array(response: Any) -> list[Any]:
        """Assert the json array."""
        data = response.json()
        assert isinstance(data, list), f"Expected JSON array, got {type(data)}"
        return data

    @staticmethod
    def assert_has_key(data: dict[str, Any], key: str) -> None:
        """Assert the has key."""
        assert key in data, f"Expected key '{key}' not found in response"

    @staticmethod
    def assert_key_value(data: dict[str, Any], key: str, expected: Any) -> None:
        """Assert the key value."""
        Assertions.assert_has_key(data, key)
        assert data[key] == expected, f"Expected {key}={expected}, got {data[key]}"

    @staticmethod
    def assert_success(data: dict[str, Any]) -> None:
        """Assert the success."""
        Assertions.assert_has_key(data, "success")
        assert data["success"] is True, f"Expected success=True, got {data['success']}"

    @staticmethod
    def assert_error(data: dict[str, Any]) -> None:
        """Assert the error."""
        Assertions.assert_has_key(data, "error")
        assert isinstance(data["error"], dict), "Expected error object"

    @staticmethod
    def assert_error_code(data: dict[str, Any], code: str) -> None:
        """Assert the error code."""
        Assertions.assert_error(data)
        error = data["error"]
        assert error.get("code") == code, f"Expected error code {code}, got {error.get('code')}"

    @staticmethod
    def assert_validation_error(data: dict[str, Any], field: str | None = None) -> None:
        """Assert the validation error."""
        Assertions.assert_error_code(data, "FX-VAL-001")
        error = data.get("error", {})
        fields = error.get("fields", {})
        if field:
            assert field in fields, f"Expected validation error for field '{field}'"

    @staticmethod
    def assert_redirect(response: Any, expected_location: str | None = None) -> None:
        """Assert the redirect."""
        status = response.status_code
        assert status in {
            301,
            302,
            303,
            307,
            308,
        }, f"Expected redirect status, got {status}"

        if expected_location:
            location = response.headers.get("location")
            assert location == expected_location, f"Expected redirect to {expected_location}, got {location}"

    @staticmethod
    def assert_header(response: Any, key: str, expected: str | None = None) -> None:
        """Assert the header."""
        assert key in response.headers, f"Expected header '{key}' not found"

        if expected:
            assert response.headers[key] == expected, (
                f"Expected header {key}={expected}, got {response.headers[key]}"
            )
