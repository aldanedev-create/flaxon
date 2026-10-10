from __future__ import annotations

from .config import AdminConfig
from .dashboard import AdminDashboard
from .decorators import admin_action, admin_display, admin_model
from .exceptions import AdminError, ModelNotFoundError, PermissionDeniedError
from .registry import Registry
from .views import AdminView, ChangeListView, CreateView, DeleteView, DetailView, UpdateView
from .services import (
    AdminActivity,
    AdminAuth,
    AdminRateLimit,
    AdminStore,
    PostgreSQLAdminStore,
    AdminStoreSessionBackend,
    RedisAdminSessionBackend,
)
from .authorization import (
    AsyncAuthorizationProvider,
    AuthorizationProvider,
    CasbinAuthorizationProvider,
    DefaultAuthorizationProvider,
    PermissionCatalog,
    PermissionDefinition,
    RedisPolicySynchronizer,
    canonical_model_permission,
    default_group_definitions,
)
from .production import (
    DurableJob,
    DurableJobStore,
    DurableJobWorker,
    ImmutableAuditLog,
    NotificationService,
    ResumableUploadStore,
    WebAuthnService,
)
from .migrations import ADMIN_SCHEMA_DOWN, ADMIN_SCHEMA_UP, write_admin_migration

from flaxon._imports import import_attribute

__all__ = [
    "ADMIN_SCHEMA_DOWN",
    "ADMIN_SCHEMA_UP",
    "AdminActivity",
    "AdminAuth",
    "AdminConfig",
    "AdminControlPlane",
    "AdminControlPlaneModule",
    "AdminDashboard",
    "AdminError",
    "AdminRateLimit",
    "AdminStore",
    "AdminStoreSessionBackend",
    "AdminView",
    "AsyncAuthorizationProvider",
    "AuthorizationProvider",
    "CasbinAuthorizationProvider",
    "ChangeListView",
    "CreateView",
    "DefaultAuthorizationProvider",
    "DeleteView",
    "DetailView",
    "DurableJob",
    "DurableJobStore",
    "DurableJobWorker",
    "EventBus",
    "ImmutableAuditLog",
    "ModelNotFoundError",
    "NotificationService",
    "PermissionCatalog",
    "PermissionDefinition",
    "PermissionDeniedError",
    "PostgreSQLAdminStore",
    "RedisAdminSessionBackend",
    "RedisPolicySynchronizer",
    "Registry",
    "RemoteModelAdapter",
    "RemoteServiceClient",
    "RemoteServiceError",
    "ResumableUploadStore",
    "ServiceRecord",
    "ServiceRegistry",
    "ServiceTokenManager",
    "UpdateView",
    "WebAuthnService",
    "admin_action",
    "admin_display",
    "admin_model",
    "canonical_model_permission",
    "default_group_definitions",
    "write_admin_migration",
]

_MICROSERVICE_EXPORTS = {
    "AdminControlPlane",
    "AdminControlPlaneModule",
    "EventBus",
    "RemoteModelAdapter",
    "RemoteServiceClient",
    "RemoteServiceError",
    "ServiceRecord",
    "ServiceRegistry",
    "ServiceTokenManager",
}


def __getattr__(name: str):
    if name in _MICROSERVICE_EXPORTS:
        microservices = import_attribute("flaxon.admin", "microservices")

        return getattr(microservices, name)
    raise AttributeError(name)
