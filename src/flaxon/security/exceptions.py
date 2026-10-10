from __future__ import annotations

from flaxon.exceptions import FlaxonError


class SecurityError(FlaxonError):
    """Report a security failure."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class AuthenticationError(SecurityError):
    """Report a authentication failure."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class AuthorizationError(SecurityError):
    """Report a authorization failure."""

    def __init__(self, message: str = "Authorization failed") -> None:
        super().__init__(message)


class TokenError(SecurityError):
    """Report a token failure."""

    def __init__(self, message: str = "Invalid token") -> None:
        super().__init__(message)


class TokenExpiredError(TokenError):
    """Report a token expired failure."""

    def __init__(self, message: str = "Token has expired") -> None:
        super().__init__(message)


class TokenInvalidError(TokenError):
    """Report a token invalid failure."""

    def __init__(self, message: str = "Invalid token") -> None:
        super().__init__(message)


class PermissionDeniedError(AuthorizationError):
    """Report a permission denied failure."""

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message)


# Preserve the established public exception import.
PermissionDenied = PermissionDeniedError


class RateLimitExceededError(SecurityError):
    """Report a rate limit exceeded failure."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message)


# Preserve the established public exception import.
RateLimitExceeded = RateLimitExceededError


class EncryptionError(SecurityError):
    """Report a encryption failure."""

    def __init__(self, message: str = "Encryption error") -> None:
        super().__init__(message)


class DecryptionError(SecurityError):
    """Report a decryption failure."""

    def __init__(self, message: str = "Decryption error") -> None:
        super().__init__(message)
