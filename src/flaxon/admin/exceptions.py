from __future__ import annotations

from flaxon.exceptions import FlaxonError


class AdminError(FlaxonError):
    pass


class ModelNotFoundError(AdminError):
    pass


class PermissionDeniedError(AdminError):
    pass


class ValidationError(AdminError):
    pass
