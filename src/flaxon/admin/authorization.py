"""Permission definitions and pluggable authorization for the Admin.

The Admin stores stable machine keys, while applications and the bundled UI
work with labels, categories, and descriptions.  The default provider keeps
the existing permission format working during migrations; strict mode removes
the legacy broad ``admin:read``/``admin:write`` fallbacks.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class PermissionDefinition:
    """A permission displayed in the Admin permission matrix."""

    key: str
    label: str
    category: str
    description: str = ""
    dangerous: bool = False


class AuthorizationProvider(Protocol):
    """Synchronous authorization contract used at request boundaries."""

    def has_permission(self, user: Any, permission: str, resource: Any = None) -> bool:
        """Return whether ``user`` may perform ``permission``."""


class AsyncAuthorizationProvider(Protocol):
    """Optional contract for providers backed by a remote policy service."""

    async def has_permission(self, user: Any, permission: str, resource: Any = None) -> bool:
        """Return whether ``user`` may perform ``permission`` asynchronously."""


def canonical_model_permission(model_name: str, action: str) -> str:
    """Return a readable, stable model permission key.

    The shape follows the familiar ``app.action_model`` convention while
    avoiding a dependency on a particular ORM or application registry.
    """

    actions = {"read": "view", "create": "add", "update": "change", "delete": "delete"}
    verb = actions.get(action, action)
    return f"{model_name}.{verb}_{model_name}"


def legacy_model_permission(model_name: str, action: str) -> str:
    """Return the pre-catalog permission key used by older applications."""

    return f"{model_name}:{action}"


class PermissionCatalog:
    """Application-local catalog of readable Admin capabilities."""

    def __init__(self) -> None:
        self._definitions: dict[str, PermissionDefinition] = {}
        self._aliases: dict[str, str] = {}
        self.register(
            "admin.superuser",
            "Full administrator access",
            "Administration",
            "Bypass normal capability checks. Assign only to protected system groups.",
            dangerous=True,
            aliases=("admin:superuser",),
        )
        self.register(
            "admin.view_dashboard",
            "View dashboard",
            "Administration",
            "Open the Admin dashboard and read operational data.",
            aliases=("admin:read",),
        )
        self.register(
            "admin.manage_users",
            "Manage users",
            "Administration",
            "Create, edit, deactivate, and remove Admin accounts.",
            dangerous=True,
            aliases=("admin:users",),
        )
        self.register(
            "admin.manage_groups",
            "Manage groups and permissions",
            "Administration",
            "Create groups and assign capabilities.",
            dangerous=True,
        )
        self.register(
            "admin.manage_settings",
            "Manage settings",
            "Administration",
            "Change application Admin settings.",
            dangerous=True,
            aliases=("admin:settings",),
        )
        self.register(
            "admin.manage_profile",
            "Manage own profile",
            "Administration",
            "Change your own password, email, and authentication methods.",
            aliases=("admin:profile",),
        )
        self.register(
            "media.manage_library",
            "Manage media library",
            "Media",
            "Upload, edit, and remove media assets.",
            aliases=("admin:media",),
        )
        self.register(
            "cms.publish_content",
            "Publish content",
            "CMS",
            "Move editorial content into the published state.",
            dangerous=True,
        )
        self.register(
            "cms.moderate_comments",
            "Moderate comments",
            "CMS",
            "Approve, reject, mark spam, or remove comments.",
        )
        self.register(
            "cms.manage_taxonomies",
            "Manage taxonomies",
            "CMS",
            "Create and edit categories, tags, and taxonomy terms.",
        )
        self.register(
            "cms.manage_menus",
            "Manage menus",
            "CMS",
            "Create and edit navigation menus and hierarchy.",
        )
        self.register(
            "cms.import_content",
            "Import content",
            "CMS",
            "Import validated content records.",
            dangerous=True,
        )
        self.register(
            "cms.export_content",
            "Export content",
            "CMS",
            "Export content records.",
        )
        self.register(
            "cms.restore_revision",
            "Restore revisions",
            "CMS",
            "Restore a previous content revision.",
            dangerous=True,
        )

    def register(
        self,
        key: str,
        label: str,
        category: str,
        description: str = "",
        *,
        dangerous: bool = False,
        aliases: Iterable[str] = (),
    ) -> PermissionDefinition:
        """Register a capability and optional migration aliases."""

        definition = PermissionDefinition(key, label, category, description, dangerous)
        self._definitions[key] = definition
        for alias in aliases:
            self._aliases[alias] = key
        return definition

    def register_model(self, model_name: str, label: str | None = None) -> list[PermissionDefinition]:
        """Register the four standard permissions for an Admin model."""

        title = label or model_name.replace("_", " ").title()
        definitions = []
        for action, verb, dangerous in (
            ("read", "view", False),
            ("create", "add", False),
            ("update", "change", False),
            ("delete", "delete", True),
        ):
            key = canonical_model_permission(model_name, action)
            definitions.append(
                self.register(
                    key,
                    f"{verb.title()} {title}",
                    title,
                    f"{verb.title()} {title.lower()} records in Admin.",
                    dangerous=dangerous,
                    aliases=(legacy_model_permission(model_name, action),),
                )
            )
        return definitions

    def get(self, key: str) -> PermissionDefinition | None:
        return self._definitions.get(self._aliases.get(key, key))

    def resolve(self, key: str) -> str:
        return self._aliases.get(key, key)

    def list_all(self) -> list[PermissionDefinition]:
        return list(self._definitions.values())

    def grouped(self) -> dict[str, list[PermissionDefinition]]:
        grouped: dict[str, list[PermissionDefinition]] = {}
        for definition in self._definitions.values():
            grouped.setdefault(definition.category, []).append(definition)
        return grouped

    def permission_choices(self) -> list[dict[str, Any]]:
        return [
            {
                "key": item.key,
                "label": item.label,
                "category": item.category,
                "description": item.description,
                "dangerous": item.dangerous,
            }
            for item in self._definitions.values()
        ]


def default_group_definitions(strict: bool = True) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Return named built-in groups and their descriptions.

    The legacy ``staff``/``editor`` names remain available so existing user
    records do not break. New deployments can use the descriptive names in
    the Admin UI instead of typing permission keys.
    """

    if strict:
        staff = ["admin.view_dashboard", "admin.manage_profile"]
        editor = ["admin.view_dashboard", "admin.manage_profile", "media.manage_library"]
    else:
        staff = ["admin:read", "admin:write"]
        editor = ["admin:read", "admin:write", "admin:media"]
    roles = {
        "staff": staff,
        "editor": editor,
        "administrator": ["admin.superuser"],
        "content_editor": ["admin.view_dashboard", "admin.manage_profile", "cms.manage_taxonomies", "cms.import_content"],
        "publisher": ["admin.view_dashboard", "admin.manage_profile", "cms.publish_content", "cms.restore_revision"],
        "media_manager": ["admin.view_dashboard", "admin.manage_profile", "media.manage_library"],
        "warehouse_staff": ["admin.view_dashboard", "admin.manage_profile"],
        "support_agent": ["admin.view_dashboard", "admin.manage_profile"],
        "read_only": ["admin.view_dashboard"],
    }
    descriptions = {
        "staff": "Basic Admin access for internal staff.",
        "editor": "Legacy editorial group retained for compatibility.",
        "administrator": "Protected group with full administrative access.",
        "content_editor": "Create and maintain editorial content without publishing it.",
        "publisher": "Review, restore, and publish approved editorial content.",
        "media_manager": "Upload, organize, validate, and maintain media assets.",
        "warehouse_staff": "Read operational records needed for fulfillment work.",
        "support_agent": "Read operational data needed to help users.",
        "read_only": "Read-only access to permitted Admin screens.",
    }
    return roles, descriptions


class DefaultAuthorizationProvider:
    """Built-in group and direct-permission evaluator.

    ``strict=False`` preserves legacy applications while their stored roles
    migrate. New deployments can set ``strict_permissions=True`` on Admin to
    require only exact model and capability keys.
    """

    def __init__(self, role_permissions: Callable[[], dict[str, list[str]]], *, strict: bool = False) -> None:
        self._role_permissions = role_permissions
        self.strict = strict

    def has_permission(self, user: Any, permission: str, resource: Any = None) -> bool:
        if user is None:
            return False
        direct = set(getattr(user, "permissions", []) or [])
        assigned = {
            value
            for role in (getattr(user, "roles", []) or [])
            for value in self._role_permissions().get(role, [])
        }
        values = direct | assigned
        if "admin:superuser" in values or "admin.superuser" in values:
            return True
        candidates = {permission}
        if "." in permission and "_" in permission:
            model_name, action_model = permission.split(".", 1)
            action = action_model.split("_", 1)[0]
            legacy_action = {"view": "read", "add": "create", "change": "update"}.get(action, action)
            candidates.add(f"{model_name}:{legacy_action}")
        if candidates & values:
            return True
        if self.strict:
            return False
        if permission == "admin.view_dashboard":
            return "admin:read" in values
        if permission in {"admin.manage_users", "admin.manage_groups"}:
            return "admin:users" in values
        if permission == "admin.manage_settings":
            return "admin:settings" in values
        if permission == "media.manage_library":
            return "admin:media" in values
        if permission == "admin.manage_profile":
            return "admin:write" in values
        if permission.startswith("cms.") and permission not in {"cms.export_content"}:
            return "admin:write" in values
        if ".view_" in permission or permission.endswith(":read"):
            return "admin:read" in values
        if any(token in permission for token in (".add_", ".change_", ".delete_", ":create", ":update", ":delete")):
            return "admin:write" in values
        return False


class CasbinAuthorizationProvider:
    """Optional adapter for applications that already use PyCasbin.

    Flaxon does not import Casbin at module import time. Pass an initialized
    enforcer (or a compatible object exposing ``enforce``) and policies remain
    owned by the application. Roles are checked first, followed by the user's
    stable username and id.
    """

    def __init__(self, enforcer: Any) -> None:
        if not hasattr(enforcer, "enforce"):
            raise TypeError("Casbin provider requires an enforcer with enforce()")
        self.enforcer = enforcer

    def has_permission(self, user: Any, permission: str, resource: Any = None) -> bool:
        if user is None:
            return False
        subject_candidates = [
            str(getattr(user, "username", "")),
            str(getattr(user, "id", "")),
            *(str(role) for role in (getattr(user, "roles", []) or [])),
        ]
        object_name = resource if isinstance(resource, str) else permission.split(".", 1)[0]
        for subject in filter(None, subject_candidates):
            if bool(self.enforcer.enforce(subject, object_name, permission)):
                return True
        return False


class RedisPolicySynchronizer:
    """Synchronize application-owned Casbin policies across workers.

    The class intentionally does not import Redis until it is used. Pass a
    shared async Redis client in tests or provide ``redis_url`` in production.
    A policy change is a cache-invalidation event; each worker reloads its
    policy through the enforcer's ``load_policy`` method.
    """

    def __init__(
        self,
        enforcer: Any,
        *,
        redis_url: str | None = None,
        redis_client: Any | None = None,
        channel: str = "flaxon:admin:policy",
        protocol: int = 2,
        max_connections: int = 100,
    ) -> None:
        if not hasattr(enforcer, "load_policy"):
            raise TypeError("Policy synchronization requires an enforcer with load_policy()")
        if redis_client is None and not redis_url:
            raise ValueError("redis_url or redis_client is required")
        self.enforcer = enforcer
        self.redis_url = redis_url
        self.redis_client = redis_client
        self.channel = channel
        self.protocol = protocol
        self.max_connections = max_connections
        self._pubsub: Any | None = None

    async def _client(self) -> Any:
        if self.redis_client is None:
            import redis.asyncio as redis

            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                protocol=self.protocol,
                max_connections=self.max_connections,
            )
        return self.redis_client

    async def publish(self) -> int:
        client = await self._client()
        return int(await client.publish(self.channel, json.dumps({"event": "policy_changed"})))

    async def reload(self) -> Any:
        result = self.enforcer.load_policy()
        return await result if isawaitable(result) else result

    async def listen_once(self, timeout: float = 1.0) -> bool:
        client = await self._client()
        if self._pubsub is None:
            self._pubsub = client.pubsub()
            await self._pubsub.subscribe(self.channel)
        message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
        if not message:
            return False
        await self.reload()
        return True

    async def listen(self, stop_event: Any | None = None, timeout: float = 1.0) -> None:
        while stop_event is None or not stop_event.is_set():
            await self.listen_once(timeout)

    async def close(self) -> None:
        if self._pubsub is not None:
            close = getattr(self._pubsub, "aclose", None) or getattr(self._pubsub, "close", None)
            if close:
                result = close()
                if isawaitable(result):
                    await result
            self._pubsub = None
        if self.redis_client is not None and self.redis_url:
            close = getattr(self.redis_client, "aclose", None) or getattr(self.redis_client, "close", None)
            if close:
                result = close()
                if isawaitable(result):
                    await result
            self.redis_client = None
