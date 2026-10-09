"""
HTTP exceptions for Flaxon.

This module provides HTTP-specific exceptions.
"""

from __future__ import annotations

from flaxon.exceptions import HTTPException


class BadRequest(HTTPException):
    """Raised when the request is malformed."""

    def __init__(self, detail: str = "Bad request.", code: str | None = None) -> None:
        """
        Initialize the exception.

        Args:
            detail: The error detail.
            code: The error code.
        """
        super().__init__(400, detail, code=code or "FX-HTTP-400")


class Unauthorized(HTTPException):
    """Raised when authentication is required."""

    def __init__(
        self,
        detail: str = "Authentication required.",
        scheme: str = "Bearer",
        code: str | None = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            detail: The error detail.
            scheme: The authentication scheme.
            code: The error code.
        """
        super().__init__(
            401,
            detail,
            code=code or "FX-HTTP-401",
            headers={"WWW-Authenticate": scheme},
        )


class Forbidden(HTTPException):
    """Raised when the user does not have permission."""

    def __init__(self, detail: str = "You do not have permission.", code: str | None = None) -> None:
        """
        Initialize the exception.

        Args:
            detail: The error detail.
            code: The error code.
        """
        super().__init__(403, detail, code=code or "FX-HTTP-403")


class NotFound(HTTPException):
    """Raised when a resource is not found."""

    def __init__(
        self, detail: str = "The requested resource was not found.", code: str | None = None
    ) -> None:
        """
        Initialize the exception.

        Args:
            detail: The error detail.
            code: The error code.
        """
        super().__init__(404, detail, code=code or "FX-HTTP-404")


class MethodNotAllowed(HTTPException):
    """Raised when an HTTP method is not allowed."""

    def __init__(self, allowed: set[str], code: str | None = None) -> None:
        """
        Initialize the exception.

        Args:
            allowed: The allowed methods.
            code: The error code.
        """
        headers = {"Allow": ", ".join(sorted(allowed))}
        super().__init__(
            405,
            "The HTTP method is not allowed for this route.",
            code=code or "FX-HTTP-405",
            headers=headers,
        )
        self.allowed = allowed


class Conflict(HTTPException):
    """Raised when there is a conflict with the current state."""

    def __init__(self, detail: str = "Conflict.", code: str | None = None) -> None:
        """
        Initialize the exception.

        Args:
            detail: The error detail.
            code: The error code.
        """
        super().__init__(409, detail, code=code or "FX-HTTP-409")


class UnprocessableEntity(HTTPException):
    """Raised when the request is semantically invalid."""

    def __init__(self, detail: str = "Unprocessable entity.", code: str | None = None) -> None:
        """
        Initialize the exception.

        Args:
            detail: The error detail.
            code: The error code.
        """
        super().__init__(422, detail, code=code or "FX-HTTP-422")


class TooManyRequests(HTTPException):
    """Raised when the rate limit is exceeded."""

    def __init__(
        self,
        detail: str = "Too many requests. Please try again later.",
        retry_after: int = 60,
        code: str | None = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            detail: The error detail.
            retry_after: The retry-after seconds.
            code: The error code.
        """
        super().__init__(
            429,
            detail,
            code=code or "FX-HTTP-429",
            headers={"Retry-After": str(retry_after)},
        )


class InternalServerError(HTTPException):
    """Raised when an internal server error occurs."""

    def __init__(self, detail: str = "Internal server error.", code: str | None = None) -> None:
        """
        Initialize the exception.

        Args:
            detail: The error detail.
            code: The error code.
        """
        super().__init__(500, detail, code=code or "FX-HTTP-500")


class ServiceUnavailable(HTTPException):
    """Raised when the service is unavailable."""

    def __init__(
        self,
        detail: str = "Service unavailable.",
        retry_after: int | None = None,
        code: str | None = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            detail: The error detail.
            retry_after: The retry-after seconds.
            code: The error code.
        """
        headers = {}
        if retry_after is not None:
            headers["Retry-After"] = str(retry_after)
        super().__init__(503, detail, code=code or "FX-HTTP-503", headers=headers)


class RequestTimeout(HTTPException):
    """Raised when the request times out."""

    def __init__(self, detail: str = "Request timed out.", code: str | None = None) -> None:
        """
        Initialize the exception.

        Args:
            detail: The error detail.
            code: The error code.
        """
        super().__init__(408, detail, code=code or "FX-HTTP-408")


class PayloadTooLarge(HTTPException):
    """Raised when the request payload is too large."""

    def __init__(
        self,
        detail: str = "Request payload too large.",
        max_size: int | None = None,
        code: str | None = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            detail: The error detail.
            max_size: The maximum size allowed.
            code: The error code.
        """
        if max_size:
            detail = f"{detail} (max: {max_size} bytes)"
        super().__init__(413, detail, code=code or "FX-HTTP-413")


class UnsupportedMediaType(HTTPException):
    """Raised when the media type is unsupported."""

    def __init__(
        self,
        detail: str = "Unsupported media type.",
        media_type: str | None = None,
        code: str | None = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            detail: The error detail.
            media_type: The unsupported media type.
            code: The error code.
        """
        if media_type:
            detail = f"{detail} (got: {media_type})"
        super().__init__(415, detail, code=code or "FX-HTTP-415")
