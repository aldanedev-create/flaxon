from __future__ import annotations

from .actions import (
    BULK,
    SINGLE,
    STANDALONE,
    Action,
    ActionContext,
    ActionResult,
    ApproveOrders,
    ExportCsv,
    Prompt,
)
from .config import AdminConfig
from .dashboard import AdminDashboard
from .extensions import (
    ADMIN_EXTENSION_GROUP,
    EXTENSION_DISTRIBUTION_PREFIX,
    AdminExtension,
    Component,
    ExtensionError,
    ExtensionPage,
    TeloceCard,
    TeloceField,
    Tool,
    load_extensions,
)
from .filters import BooleanFilter, DateRangeFilter, Filter, SelectFilter
from .impersonation import ImpersonationManager
from .lenses import Lens
from .policies import Policy
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
from .metrics import (
    PARTITION,
    PROGRESS,
    TABLE,
    TREND,
    VALUE,
    Metric,
    MetricRange,
    Partition,
    Progress,
    Table,
    Trend,
    TTLCache,
    Value,
    resolve_range,
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
    "ADMIN_EXTENSION_GROUP",
    "ADMIN_SCHEMA_DOWN",
    "ADMIN_SCHEMA_UP",
    "BULK",
    "EXTENSION_DISTRIBUTION_PREFIX",
    "PARTITION",
    "PROGRESS",
    "SINGLE",
    "STANDALONE",
    "TABLE",
    "TREND",
    "VALUE",
    "Action",
    "ActionContext",
    "ActionResult",
    "AdminActivity",
    "AdminAuth",
    "AdminConfig",
    "AdminControlPlane",
    "AdminControlPlaneModule",
    "AdminDashboard",
    "AdminError",
    "AdminExtension",
    "AdminRateLimit",
    "AdminStore",
    "AdminStoreSessionBackend",
    "AdminView",
    "ApproveOrders",
    "AsyncAuthorizationProvider",
    "AuthorizationProvider",
    "BooleanFilter",
    "CasbinAuthorizationProvider",
    "ChangeListView",
    "Component",
    "CreateView",
    "DateRangeFilter",
    "DefaultAuthorizationProvider",
    "DeleteView",
    "DetailView",
    "DurableJob",
    "DurableJobStore",
    "DurableJobWorker",
    "EventBus",
    "ExportCsv",
    "ExtensionError",
    "ExtensionPage",
    "Filter",
    "ImmutableAuditLog",
    "ImpersonationManager",
    "Lens",
    "Metric",
    "MetricRange",
    "ModelNotFoundError",
    "NotificationService",
    "Partition",
    "PermissionCatalog",
    "PermissionDefinition",
    "PermissionDeniedError",
    "Policy",
    "PostgreSQLAdminStore",
    "Progress",
    "Prompt",
    "RedisAdminSessionBackend",
    "RedisPolicySynchronizer",
    "Registry",
    "RemoteModelAdapter",
    "RemoteServiceClient",
    "RemoteServiceError",
    "ResumableUploadStore",
    "SelectFilter",
    "ServiceRecord",
    "ServiceRegistry",
    "ServiceTokenManager",
    "TTLCache",
    "Table",
    "TeloceCard",
    "TeloceField",
    "Tool",
    "Trend",
    "UpdateView",
    "Value",
    "WebAuthnService",
    "admin_action",
    "admin_display",
    "admin_model",
    "canonical_model_permission",
    "default_group_definitions",
    "load_extensions",
    "resolve_range",
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
