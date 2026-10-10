from __future__ import annotations

from flaxon.exceptions import FlaxonError


class DatabaseError(FlaxonError):
    """Report a database failure."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class ConnectionError(DatabaseError):
    """Report a connection failure."""

    def __init__(self, message: str = "Database connection error") -> None:
        """Perform the   init   operation for connection error."""
        super().__init__(message)


class QueryError(DatabaseError):
    """Report a query failure."""

    def __init__(self, message: str = "Database query error", query: str | None = None) -> None:
        super().__init__(message)
        self.query = query


class TransactionError(DatabaseError):
    """Report a transaction failure."""

    def __init__(self, message: str = "Transaction error") -> None:
        super().__init__(message)


class MigrationError(DatabaseError):
    """Report a migration failure."""

    def __init__(self, message: str = "Migration error") -> None:
        super().__init__(message)


class IntegrityError(DatabaseError):
    """Report a integrity failure."""

    def __init__(self, message: str = "Integrity constraint violated") -> None:
        super().__init__(message)


class NotFoundError(DatabaseError):
    """Report a not found failure."""

    def __init__(self, message: str = "Record not found") -> None:
        super().__init__(message)


class DuplicateError(DatabaseError):
    """Report a duplicate failure."""

    def __init__(self, message: str = "Duplicate record") -> None:
        super().__init__(message)
