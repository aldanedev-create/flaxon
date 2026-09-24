from __future__ import annotations

from .config import AdminConfig
from .dashboard import AdminDashboard
from .decorators import admin_action, admin_display, admin_model
from .exceptions import AdminError, ModelNotFoundError, PermissionDeniedError
from .registry import Registry
from .views import AdminView, ChangeListView, CreateView, DeleteView, DetailView, UpdateView
from .services import AdminActivity, AdminAuth, AdminRateLimit, AdminStore, PostgreSQLAdminStore, AdminStoreSessionBackend, RedisAdminSessionBackend
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
from .production import DurableJob, DurableJobStore, DurableJobWorker, ImmutableAuditLog, NotificationService, ResumableUploadStore, WebAuthnService
from .migrations import ADMIN_SCHEMA_DOWN, ADMIN_SCHEMA_UP, write_admin_migration

__all__ = [
    "AdminDashboard",
    "AdminConfig",
    "Registry",
    "AdminView",
    "ChangeListView",
    "DetailView",
    "CreateView",
    "UpdateView",
    "DeleteView",
    "admin_model",
    "admin_action",
    "admin_display",
    "AdminError",
    "ModelNotFoundError",
    "PermissionDeniedError",
    "AdminActivity",
    "AdminAuth",
    "AdminRateLimit",
    "AdminStore",
    "PostgreSQLAdminStore",
    "AdminStoreSessionBackend",
    "RedisAdminSessionBackend",
    "AuthorizationProvider",
    "AsyncAuthorizationProvider",
    "CasbinAuthorizationProvider",
    "DefaultAuthorizationProvider",
    "PermissionCatalog",
    "PermissionDefinition",
    "RedisPolicySynchronizer",
    "canonical_model_permission",
    "default_group_definitions",
    "DurableJob",
    "DurableJobStore",
    "DurableJobWorker",
    "ImmutableAuditLog",
    "NotificationService",
    "ResumableUploadStore",
    "WebAuthnService",
    "AdminControlPlane",
    "AdminControlPlaneModule",
    "EventBus",
    "RemoteModelAdapter",
    "RemoteServiceClient",
    "RemoteServiceError",
    "ServiceRecord",
    "ServiceRegistry",
    "ServiceTokenManager",
    "ADMIN_SCHEMA_UP",
    "ADMIN_SCHEMA_DOWN",
    "write_admin_migration",
]

_MICROSERVICE_EXPORTS = {
    "AdminControlPlane", "AdminControlPlaneModule", "EventBus", "RemoteModelAdapter",
    "RemoteServiceClient", "RemoteServiceError", "ServiceRecord", "ServiceRegistry", "ServiceTokenManager",
}


def __getattr__(name: str):
    if name in _MICROSERVICE_EXPORTS:
        from . import microservices

        return getattr(microservices, name)
    raise AttributeError(name)
