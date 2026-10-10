from __future__ import annotations

from flaxon.exceptions import FlaxonError


class AdminError(FlaxonError):
    """Report a admin failure."""

    pass


class ModelNotFoundError(AdminError):
    """Report a model not found failure."""

    pass


class PermissionDeniedError(AdminError):
    """Report a permission denied failure."""

    pass


class ValidationError(AdminError):
    """Report a validation failure."""

    pass
