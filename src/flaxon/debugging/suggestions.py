from __future__ import annotations

from typing import Any, ClassVar


class SuggestionEngine:
    """Suggestion engine implementation for the debugging subsystem."""

    COMMON_ERRORS: ClassVar[Any] = {
        "No module named": "You need to install a missing dependency. Run: pip install <module>",
        (
            "ImportError"
        ): "There is an import error. Check that all modules are installed and paths are correct.",
        "AttributeError": "You are trying to access an attribute that doesn't exist. Check the object type.",
        "TypeError": "You are using the wrong type for an operation. Check your types.",
        "ValueError": "You passed an invalid value. Check the allowed values for this operation.",
        "KeyError": "You are trying to access a dictionary key that doesn't exist. Check the key name.",
        "IndexError": "You are trying to access a list index that doesn't exist. Check the list length.",
        "ZeroDivisionError": "You are dividing by zero. Check your divisor.",
        "FileNotFoundError": "The file does not exist. Check the file path.",
        "PermissionError": "You do not have permission to access this file. Check file permissions.",
        "ConnectionError": "There is a connection issue. Check your network and the remote server.",
        "TimeoutError": "The operation timed out. Try increasing the timeout or check the remote server.",
        "RuntimeError": "A runtime error occurred. Check the error message for details.",
        "NotImplementedError": "This feature is not yet implemented.",
        "OSError": "An operating system error occurred. Check file paths and permissions.",
    }

    ROUTING_ERRORS: ClassVar[Any] = {
        "404": "The route you requested was not found. Check the URL path.",
        "405": "The HTTP method is not allowed for this route. Check the allowed methods.",
        "MethodNotAllowed": "The HTTP method is not allowed for this route. Check the allowed methods.",
        "route not found": "The requested route does not exist. Check your route registration.",
        "Router": "There is an issue with the router. Check your route definitions.",
    }

    VALIDATION_ERRORS: ClassVar[Any] = {
        "ValidationError": "The request data failed validation. Check the required fields and types.",
        "required": "A required field is missing. Check the schema definition.",
        "min_length": "The value is too short. Check the minimum length requirement.",
        "max_length": "The value is too long. Check the maximum length requirement.",
        "min_value": "The value is too small. Check the minimum value requirement.",
        "max_value": "The value is too large. Check the maximum value requirement.",
        "email": "The email address is invalid. Check the email format.",
        "url": "The URL is invalid. Check the URL format.",
        "pattern": "The value does not match the required pattern. Check the regex pattern.",
        "choice": "The value is not in the list of allowed choices. Check the choices.",
    }

    DATABASE_ERRORS: ClassVar[Any] = {
        (
            "IntegrityError"
        ): "There is a database integrity issue. Check for duplicate keys or foreign key violations.",
        "UniqueViolation": "A duplicate value was inserted. Check for uniqueness constraints.",
        "ForeignKeyViolation": "A foreign key reference is invalid. Check the referenced record exists.",
        "NotNullViolation": "A required field is null. Check the field is provided.",
        "Connection refused": "Could not connect to the database. Check the database connection settings.",
        "database": "There is a database issue. Check your database connection and queries.",
    }

    def get_suggestion(self, error: Exception) -> str | None:
        """Return the suggestion."""
        error_str = str(error)
        error_type = type(error).__name__

        combined = f"{error_type}: {error_str}"

        for pattern, suggestion in self.COMMON_ERRORS.items():
            if pattern.lower() in combined.lower():
                return suggestion

        for pattern, suggestion in self.ROUTING_ERRORS.items():
            if pattern.lower() in combined.lower():
                return suggestion

        for pattern, suggestion in self.VALIDATION_ERRORS.items():
            if pattern.lower() in combined.lower():
                return suggestion

        for pattern, suggestion in self.DATABASE_ERRORS.items():
            if pattern.lower() in combined.lower():
                return suggestion

        return None

    def get_validation_suggestions(self, errors: dict[str, list[str]]) -> dict[str, str]:
        """Return the validation suggestions."""
        suggestions = {}
        for field, field_errors in errors.items():
            for error in field_errors:
                for pattern, suggestion in self.VALIDATION_ERRORS.items():
                    if pattern.lower() in error.lower():
                        suggestions[field] = suggestion
                        break
                if field not in suggestions:
                    suggestions[field] = "Check the field value and try again."
        return suggestions

    def suggest_fix(self, code: str) -> str | None:
        """Perform the suggest fix operation for suggestion engine."""
        suggestions = {
            "FX-HTTP-404": "Check that the URL is correct and the route is registered.",
            "FX-HTTP-405": "Check that you are using the correct HTTP method for this route.",
            "FX-HTTP-422": "Check the request data against the schema definition.",
            "FX-HTTP-429": "Reduce the request rate or increase the rate limit.",
            "FX-HTTP-500": "Check the server logs for more details about the error.",
            "FX-VAL-001": "Review the validation errors and fix the invalid fields.",
            "FX-RATE-001": "Wait for the rate limit window to expire before trying again.",
            "FX-SRV-500": "Check the server logs and application state.",
            "FX-DEV-500": "Look at the debug information above for the specific error.",
        }
        return suggestions.get(code)
