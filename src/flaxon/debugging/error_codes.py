from __future__ import annotations

from typing import Any


class ErrorCodes:
    CODES = {
        "FX-HTTP-400": {
            "status": 400,
            "message": "Bad Request",
            "suggestion": "Check your request parameters and try again.",
        },
        "FX-HTTP-401": {
            "status": 401,
            "message": "Unauthorized",
            "suggestion": "Provide valid authentication credentials.",
        },
        "FX-HTTP-403": {
            "status": 403,
            "message": "Forbidden",
            "suggestion": "You do not have permission to access this resource.",
        },
        "FX-HTTP-404": {
            "status": 404,
            "message": "Not Found",
            "suggestion": "The requested resource does not exist.",
        },
        "FX-HTTP-405": {
            "status": 405,
            "message": "Method Not Allowed",
            "suggestion": "Use an allowed HTTP method for this endpoint.",
        },
        "FX-HTTP-409": {
            "status": 409,
            "message": "Conflict",
            "suggestion": "The request conflicts with the current state of the resource.",
        },
        "FX-HTTP-422": {
            "status": 422,
            "message": "Unprocessable Entity",
            "suggestion": "Check the provided data and try again.",
        },
        "FX-HTTP-429": {
            "status": 429,
            "message": "Too Many Requests",
            "suggestion": "Slow down your request rate and try again later.",
        },
        "FX-HTTP-500": {
            "status": 500,
            "message": "Internal Server Error",
            "suggestion": "An unexpected error occurred. Contact support if the issue persists.",
        },
        "FX-VAL-001": {
            "status": 422,
            "message": "Validation Error",
            "suggestion": "Check your input data for errors and try again.",
        },
        "FX-RATE-001": {
            "status": 429,
            "message": "Rate Limit Exceeded",
            "suggestion": "You have exceeded the rate limit. Wait and try again.",
        },
        "FX-SRV-500": {
            "status": 500,
            "message": "Server Error",
            "suggestion": "An internal server error occurred. Please try again later.",
        },
        "FX-DEV-500": {
            "status": 500,
            "message": "Development Error",
            "suggestion": "Check the debug output for details.",
        },
        "FX-AUTH-001": {
            "status": 401,
            "message": "Authentication Failed",
            "suggestion": "Invalid credentials provided.",
        },
        "FX-AUTH-002": {
            "status": 403,
            "message": "Authorization Failed",
            "suggestion": "You do not have the required permissions.",
        },
        "FX-REQ-JSON": {
            "status": 400,
            "message": "Invalid JSON",
            "suggestion": "The request body contains invalid JSON.",
        },
    }

    def get(self, code: str) -> dict[str, Any] | None:
        return self.CODES.get(code)

    def get_message(self, code: str) -> str:
        return self.CODES.get(code, {}).get("message", "Unknown error")

    def get_status(self, code: str) -> int:
        return self.CODES.get(code, {}).get("status", 500)

    def get_suggestion(self, code: str) -> str | None:
        return self.CODES.get(code, {}).get("suggestion")

    def get_by_status(self, status: int) -> list[str]:
        return [code for code, info in self.CODES.items() if info.get("status") == status]

    def register(self, code: str, status: int, message: str, suggestion: str | None = None) -> None:
        self.CODES[code] = {"status": status, "message": message, "suggestion": suggestion}

    def is_valid(self, code: str) -> bool:
        return code in self.CODES
