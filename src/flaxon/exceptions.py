"""Framework exception types and their HTTP status mappings."""

from __future__ import annotations

from typing import Any


class FlaxonError(Exception):
    """Base class for framework errors."""


class HTTPExceptionError(FlaxonError):
    """An exception that can be rendered as an HTTP response."""

    def __init__(
        self,
        status_code: int,
        detail: str | None = None,
        *,
        code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail or "HTTP error"
        self.code = code or f"FX-HTTP-{status_code}"
        self.extra = extra or {}
        super().__init__(self.detail)

    def to_dict(self) -> dict[str, Any]:
        """Return the API error payload."""
        payload: dict[str, Any] = {"code": self.code, "message": self.detail}
        payload.update(self.extra)
        return {"error": payload}


# Preserve the established public exception import.
HTTPException = HTTPExceptionError


class NotFound(HTTPException):
    """Raised when no route matches a request."""

    def __init__(self, detail: str = "Not found") -> None:
        super().__init__(404, detail)


class MethodNotAllowed(HTTPException):
    """Raised when a route exists but does not accept the method."""

    def __init__(self, detail: str = "Method not allowed") -> None:
        super().__init__(405, detail)


class BadRequest(HTTPException):
    """Raised for malformed client requests."""

    def __init__(self, detail: str = "Bad request") -> None:
        super().__init__(400, detail)


class Conflict(HTTPException):
    """Raised when a resource changed during an optimistic update."""

    def __init__(self, detail: str = "Resource conflict") -> None:
        super().__init__(409, detail)


class Unauthorized(HTTPException):
    """Raised when authentication is required or invalid."""

    def __init__(self, detail: str = "Unauthorized") -> None:
        super().__init__(401, detail)


class Forbidden(HTTPException):
    """Raised when the authenticated user lacks permission."""

    def __init__(self, detail: str = "Forbidden") -> None:
        super().__init__(403, detail)


class RequestTimeout(HTTPException):
    """Raised when request processing exceeds the allowed time."""

    def __init__(self, detail: str = "Request timeout") -> None:
        super().__init__(408, detail, code="FX-TIMEOUT-001")


class PayloadTooLarge(HTTPException):
    """Raised when a request body exceeds the configured size limit."""

    def __init__(self, max_size: int, detail: str | None = None) -> None:
        self.max_size = max_size
        super().__init__(
            413, detail or f"Request body exceeds the {max_size}-byte limit", code="FX-PAYLOAD-001"
        )


class TooManyRequests(HTTPException):
    """Raised when a rate limit is exceeded."""

    def __init__(self, detail: str = "Too many requests") -> None:
        super().__init__(429, detail, code="FX-RATE-001")


class ConfigurationError(FlaxonError):
    """Raised for invalid framework configuration."""


class DependencyError(FlaxonError):
    """Raised when a dependency cannot be resolved."""

    def __init__(self, detail: str = "Dependency error") -> None:
        self.detail = detail
        super().__init__(detail)
