Warning: truncated output (original token count: 25838)
Total output lines: 1834

from __future__ import annotations

import os
import asyncio
import time
import secrets
import csv
import io
import json
import base64
import hashlib
import mimetypes
from io import BytesIO
from pathlib import Path
from contextvars import ContextVar
from typing import Any

from flaxon.exceptions import BadRequest, Forbidden, NotFound
from flaxon.http import JSONResponse, RedirectResponse, Request, Response
from flaxon.files import FileStorage
from flaxon.security import CSRF, Sanitizer
from flaxon.security.rate_limit import DistributedRateLimiter
from flaxon.security.password import PasswordHasher
from flaxon.jinax import Jinax

from .config import AdminConfig
from .authorization import AuthorizationProvider, PermissionCatalog, canonical_model_permission, default_group_definitions
from .registry import Registry, default_registry, evaluate_permission_hook
from .views import ChangeListView, CreateView, DeleteView, DetailView, UpdateView
from .services import AdminActivity, AdminAuth, AdminRateLimit, AdminStore, AdminStoreSessionBackend, RedisAdminSessionBackend
from .production import DurableJobStore, DurableJobWorker, ImmutableAuditLog, NotificationService, ResumableUploadStore, WebAuthnService

_PACKAGE_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


class AdminDashboard:
    def __init__(
        self,
        app: Any,
        config: AdminConfig | None = None,
        url_prefix: str = "/admin",
        template_dir: str | None = None,
        registry: Registry | None = None,
        users: list[dict[str, Any]] | None = None,
        auth_backend: Any | None = None,
        upload_dir: str = "uploads",
        store: AdminStore | None = None,
        storage_path: str | None = None,
        redis_url: str | None = None,
        database: Any | None = None,
        password_reset_sender: Any | None = None,
        email_verification_sender: Any | None = None,
        require_email_verification: bool = False,
        max_upload_size: int = 10 * 1024 * 1024,
        allowed_upload_types: set[str] | None = None,
        media_storage: Any | None = None,
        redis_protocol: int = 2,
        redis_max_connections: int = 100,
        thumbnail_sync_limit: int = 2 * 1024 * 1024,
        session_idle_timeout: int | None = None,
        media_scanner: Any | None = None,
        media_retention_days: int = 365,
        webauthn_provider: Any | None = None,
        permission_provider: AuthorizationProvider | None = None,
        strict_permissions: bool = False,
        max_image_dimensions: tuple[int, int] = (10000, 10000),
        password_hasher: PasswordHasher | None = None,
        microservices: bool | dict[str, Any] = True,
        cookie_secure: bool | None = None,
        session_bound_csrf: bool = False,
    ) -> None:
        self._navigation_user = ContextVar("flaxon_admin_navigation_user", default=None)
        self.app = app
        self.config = config or AdminConfig()
        self.url_prefix = url_prefix.rstrip("/")
        self.strict_permissions = strict_permissions
        self.registry = registry if registry is not None else default_registry
        self.permission_catalog = PermissionCatalog()
        self.widgets: list[Any] = []
        self.custom_views: list[dict[str, Any]] = []
        self.hooks: dict[str, list[Any]] = {}
        self.jinax = Jinax(template_dir or _PACKAGE_TEMPLATE_DIR, auto_reload=True)
        self.jinax.add_global("dashboard", self)
        self.store = store or (AdminStore(storage_path) if storage_path else None)
        self.database = database or getattr(app, "database", None) or getattr(app, "db", None)
        self._database_loaded = False
        setattr(self.app, "_flaxon_admin_store", self.store)
        persisted_users = list((self.store.list("users") if self.store else {}).values())
        session_backend = auth_backend
        if session_backend is None:
            if redis_url:
                session_backend = RedisAdminSessionBackend(redis_url, protocol=redis_protocol, max_connections=redis_max_connections, idle_timeout=session_idle_timeout)
            elif self.store is not None:
                session_backend = AdminStoreSessionBackend(self.store, idle_timeout=session_idle_timeout)
        self.auth = AdminAuth(
            persisted_users or users,
            session_backend,
            store=self.store,
            session_idle_timeout=session_idle_timeout,
            permission_provider=permission_provider,
            strict_permissions=strict_permissions,
            password_hasher=password_hasher,
            cookie_secure=not getattr(app, "debug", False) if cookie_secure is None else cookie_secure,
        )
        self.password_reset_sender = password_reset_sender
        self.email_verification_sender = email_verification_sender
        self.require_email_verification = require_email_verification
        self.max_upload_size = max_upload_size
        self.allowed_upload_types = allowed_upload_types or {"image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf", "text/plain"}
        self.media_storage = media_storage
        self.thumbnail_sync_limit = thumbnail_sync_limit
        self.media_scanner = media_scanner
        self.media_retention_days = max(1, media_retention_days)
        self.max_image_dimensions = (max(1, int(max_image_dimensions[0])), max(1, int(max_image_dimensions[1])))
        self._thumbnail_tasks: set[asyncio.Task[Any]] = set()
        self._job_worker_task: asyncio.Task[Any] | None = None
        self._auth_rate_redis: Any = None
        self._auth_rate_limiter: DistributedRateLimiter | None = None
        self._redis_url = redis_url
        self._redis_protocol = redis_protocol
        self._redis_max_connections = redis_max_connections
        self.session_bound_csrf = session_bound_csrf
        secret = self.app.config.get("SECRET_KEY") or secrets.token_urlsafe(32)
        if session_bound_csrf:
            from .csrf import AdminCSRF, AdminCSRFMiddleware
            self.csrf = AdminCSRF(secret)
            self.app.add_middleware(AdminCSRFMiddleware, dashboard=self)
        else:
            self.csrf = CSRF(secret)
        self._csrf_token = self.csrf.generate_token()
        setattr(self.app, "_flaxon_admin_auth", self.auth)
        setattr(self.app, "_flaxon_admin_dashboard", self)
        self.activities: list[AdminActivity] = [AdminActivity(**item) for item in ((self.store.get("meta", "activities", []) if self.store else []))]
        self.notifications: list[dict[str, Any]] = (self.store.get("meta", "notifications", []) if self.store else []) or []
        self.operations: list[dict[str, Any]] = (self.store.get("operations", "records", []) if self.store else []) or []
        if self.store and hasattr(self.store, "list_operations"):
            self.operations = self.store.list_operations(1000)
        default_roles, default_descriptions = default_group_definitions(strict_permissions)
        stored_roles = self.store.get("meta", "roles", {}) if self.store else {}
        self.roles: dict[str, list[str]] = stored_roles or default_roles
        self.auth.role_permissions = self.roles
        stored_descriptions = self.store.get("meta", "role_descriptions", {}) if self.store else {}
        self.role_descriptions: dict[str, str] = {**default_descriptions, **(stored_descriptions or {})}
        self.protected_roles = set(default_descriptions)
        for registered in self.registry.get_all():
            self.permission_catalog.register_model(registered.get_name(), registered.get_verbose_name_plural())
        # Resolve legacy aliases once at startup so new role assignments are
        # stored in the readable catalog format while existing users continue
        # to authenticate without a manual data migration.
        self.roles = {
            role: sorted({self.permission_catalog.resolve(permission) for permission in permissions})
            for role, permissions in self.roles.items()
        }
        self.auth.role_permissions = self.roles
        self.job_store = DurableJobStore(self.store) if self.store else None
        self.job_worker = DurableJobWorker(self.job_store) if self.job_store else None
        self.audit_log = ImmutableAuditLog(self.store) if self.store else None
        self.notification_service = NotificationService(self.store) if self.store else None
        self.resumable_uploads = ResumableUploadStore(self.store) if self.store else None
        self.webauthn = WebAuthnService(self.store, webauthn_provider) if self.store else None
        if self.job_worker:
            self.job_worker.register("media.thumbnail", lambda payload: self._generate_thumbnail(payload["relative"], None))
        if self.store:
            saved_config = self.store.get("meta", "config")
            if saved_config:
                self.config.site_title = saved_config.get("site_title", self.config.site_title)
                self.config.site_header = saved_config.get("site_header", self.config.site_header)
                self.config.timezone = saved_config.get("timezone", self.config.timezone)
            for record in self.auth.users.values():
                self.store.set("users", record["username"], record)
        self.media = FileStorage(upload_dir)
        self.media_metadata: dict[str, dict[str, Any]] = (self.store.get("media", "metadata", {}) if self.store else {}) or {}
        self.media_folders: list[str] = (self.store.get("media", "folders", []) if self.store else []) or []
        if redis_url and hasattr(self.app, "websocket_manager"):
            from flaxon.websocket.redis_backend import RedisBroadcaster
            self._redis_broadcaster = RedisBroadcaster(redis_url, protocol=redis_protocol, max_connections=redis_max_connections)
            self.app.on_startup(lambda: self.app.websocket_manager.configure_broadcaster(self._redis_broadcaster))
            self.app.on_shutdown(self.app.websocket_manager.close_broadcaster)
        if hasattr(self.app, "mount_static"):
            self.app.mount_static("/uploads", upload_dir)
        self._mount_static()
        if hasattr(self.app, "add_middleware"):
            self.app.add_middleware(
                AdminRateLimit,
                prefix=self.url_prefix,
                redis_url=redis_url,
                redis_protocol=redis_protocol,
                redis_max_connections=redis_max_connections,
            )
        if hasattr(self.app, "on_shutdown"):
            self.app.on_shutdown(self._stop_thumbnail_tasks)
        if hasattr(self.app, "on_startup") and self.job_worker:
            self.app.on_startup(self._start_job_worker)
        self._register_routes()
        # Keep the service control plane additive. Existing model, CMS, and
        # custom-page routes remain the public compatibility surface; the
        # microservice pages reserve their own named Admin resources.
        self.control_plane = None
        if microservices is not False:
            from .microservices import AdminControlPlane

            self.control_plane = AdminControlPlane(self)

    async def _stop_thumbnail_tasks(self) -> None:
        if self._job_worker_task is not None:
            self._job_worker_task.cancel()
            await asyncio.gather(self._job_worker_task, return_exceptions=True)
            self._job_worker_task = None
        for task in tuple(self._thumbnail_tasks):
            task.cancel()
        if self._thumbnail_tasks:
            await asyncio.gather(*self._thumbnail_tasks, return_exceptions=True)
        self._thumbnail_tasks.clear()
        if self._auth_rate_redis is not None:
            await self._auth_rate_redis.aclose()
            self._auth_rate_redis = None

    async def _start_job_worker(self) -> None:
        if self.job_worker is None or self._job_worker_task is not None:
            return
        self._job_worker_task = asyncio.create_task(self._job_worker_loop())

    async def _job_worker_loop(self) -> None:
        while True:
            await self.job_worker.run_once(limit=5)
            await asyncio.sleep(0.5)

    async def _allow_auth_action(self, request: Request, action: str, account: str = "anonymous") -> bool:
        if not self._redis_url:
            return True
        if self._auth_rate_redis is None:
            import redis.asyncio as redis
            self._auth_rate_redis = redis.from_url(self._redis_url, decode_responses=True, protocol=self._redis_protocol, max_connections=self._redis_max_connections)
            self._auth_rate_limiter = DistributedRateLimiter(self._auth_rate_redis, prefix="flaxon:admin:auth")
        client = request.scope.get("client") if hasattr(request, "scope") else None
        ip = str(client[0]) if isinstance(client, (tuple, list)) and client else "unknown"
        key = f"{action}:{account.strip().lower()}:{ip}"
        return await self._auth_rate_limiter.check(key, requests=5, window_seconds=300)

    def _mount_static(self) -> None:
        if hasattr(self.app, "mount_static"):
            static_dir = os.path.join(os.path.dirname(__file__), "static")
            self.app.mount_static("/static", static_dir)

    def _register_routes(self) -> None:
        router = self.app.router

        router.get(f"{self.url_prefix}/login")(self.login)
        router.post(f"{self.url_prefix}/login")(self.login)
        router.get(f"{self.url_prefix}/password-reset")(self.password_reset)
        router.post(f"{self.url_prefix}/password-reset")(self.password_reset)
        router.get(f"{self.url_prefix}/verify-email")(self.verify_email)
        router.post(f"{self.url_prefix}/verify-email")(self.verify_email)
        router.get(f"{self.url_prefix}/logout")(self.logout)
        router.post(f"{self.url_prefix}/logout")(self.logout)
        router.get(f"{self.url_prefix}/profile")(self.profile)
        router.post(f"{self.url_prefix}/profile")(self.profile)
        router.get(f"{self.url_prefix}/users")(self.users_view)
        router.post(f"{self.url_prefix}/users")(self.users_view)
        router.get(f"{self.url_prefix}/roles")(self.roles_view)
        router.post(f"{self.url_prefix}/roles")(self.roles_view)
        router.patch(f"{self.url_prefix}/users/<username>")(self.user_api)
        router.delete(f"{self.url_prefix}/users/<username>")(self.user_api)
        router.get(f"{self.url_prefix}/media")(self.media_view)
        router.post(f"{self.url_prefix}/media")(self.media_view)
        router.post(f"{self.url_prefix}/media/resumable")(self.resumable_media)
        router.get(f"{self.url_prefix}/media/resumable/<upload_id>")(self.resumable_media)
        router.patch(f"{self.url_prefix}/media/resumable/<upload_id>")(self.resumable_media)
        router.post(f"{self.url_prefix}/media/resumable/<upload_id>/complete")(self.resumable_media)
        router.get(f"{self.url_prefix}/media/folders")(self.media_folders_api)
        router.post(f"{self.url_prefix}/media/folders")(self.media_folders_api)
        router.delete(f"{self.url_prefix}/media/folders/<path:folder>")(self.media_folders_api)
        router.post(f"{self.url_prefix}/media/bulk")(self.media_bulk_api)
        router.get(f"{self.url_prefix}/media/<path:filename>/signed-url")(self.media_signed_url)
        router.patch(f"{self.url_prefix}/media/<path:filename>")(self.media_api)
        router.delete(f"{self.url_prefix}/media/<path:filename>")(self.media_api)
        router.get(f"{self.url_prefix}/search")(self.search)
        router.get(f"{self.url_prefix}/<model_name>/export")(self.model_export)
        router.post(f"{self.url_prefix}/<model_name>/import")(self.model_import)
        router.get(f"{self.url_prefix}/<model_name>/<object_id>/history")(self.history)
        router.get(f"{self.url_prefix}/settings")(self.settings_view)
        router.post(f"{self.url_prefix}/settings")(self.settings_view)
        router.get(f"{self.url_prefix}/activity")(self.activity_view)
        router.get(f"{self.url_prefix}/activity/export")(self.activity_export)
        router.route(f"{self.url_prefix}/notifications", methods={"GET", "POST"}, name="notifications_api")(self.notifications_api)
        router.route(f"{self.url_prefix}/notifications/preferences", methods={"GET", "POST"}, name="notification_preferences")(self.notification_preferences)
        router.get(f"{self.url_prefix}/audit/verify")(self.audit_verify)
        router.post(f"{self.url_prefix}/profile/webauthn/register/begin")(self.webauthn_api)
        router.post(f"{self.url_prefix}/profile/webauthn/register/finish")(self.webauthn_api)
        router.post(f"{self.url_prefix}/profile/webauthn/authenticate/begin")(self.webauthn_api)
        router.post(f"{self.url_prefix}/profile/webauthn/authenticate/finish")(self.webauthn_api)
        router.route(f"{self.url_prefix}/profile/trusted-devices", methods={"GET", "POST"}, name="trusted_devices")(self.trusted_devices_api)
        router.delete(f"{self.url_prefix}/profile/trusted-devices/<device_id>")(self.trusted_devices_api)
        router.post(f"{self.url_prefix}/profile/mfa/recovery-codes")(self.mfa_recovery_api)
        router.get(f"{self.url_prefix}/operations")(self.operations_view)
        router.get(f"{self.url_prefix}/operations/tasks")(self.operations_tasks_api)
        router.get(f"{self.url_prefix}")(self.index)
        router.get(f"{self.url_prefix}/")(self.index)
        router.get(f"{self.url_prefix}/<model_name>")(self.list_view)
        router.get(f"{self.url_prefix}/<model_name>/add")(self.model_add_view)
        router.post(f"{self.url_prefix}/<model_name>/add")(self.model_add_view)
        router.get(f"{self.url_prefix}/<model_name>/<object_id>")(self.detail_view)
        router.get(f"{self.url_prefix}/<model_name>/<object_id>/edit")(self.edit_view)
        router.post(f"{self.url_prefix}/<model_name>/<object_id>/edit")(self.edit_view)
        router.get(f"{self.url_prefix}/<model_name>/<object_id>/delete")(self.delete_view)
        router.post(f"{self.url_prefix}/<model_name>/<object_id>/delete")(self.delete_view)
        router.post(f"{self.url_prefix}/<model_name>/actions/<action_name>")(self.model_action)

    def register(self, model: Any, **options: Any) -> None:
        """Register a model with the dashboard's registry."""
        self.registry.register(model, **options)
        registered = self.registry.get_by_model(model)
        if registered:
            self.permission_catalog.register_model(registered.get_name(), registered.get_verbose_name_plural())

    def register_widget(self, widget: Any) -> Any:
        self.widgets.append(widget)
        return widget

    async def _widget_context(self, user: Any) -> list[Any]:
        """Evaluate extension widgets once per dashboard request."""

        rendered = []
        for widget in self.widgets:
            value = widget
            if hasattr(widget, "render"):
                value = widget.render(user=user, dashboard=self)
            elif callable(widget):
                value = widget(user=user, dashboard=self)
            if hasattr(value, "__await__"):
                value = await value
            rendered.append(value)
        return rendered

    def register_permission(
        self,
        key: str,
        label: str,
        category: str = "Custom",
        description: str = "",
        *,
        dangerous: bool = False,
    ) -> Any:
        """Register an application capability for the role editor."""

        return self.permission_catalog.register(key, label, category, description, dangerous=dangerous)

    def permission_for_action(self, model_name: str, action: str) -> str:
        """Return and lazily register a model action capability."""

        key = canonical_model_permission(model_name, action)
        if self.permission_catalog.get(key) is None:
            model = self.registry.get(model_name)
            label = model.get_verbose_name_plural() if model else model_name.replace("_", " ").title()
            self.permission_catalog.register(
                key,
                f"{action.replace('_', ' ').title()} {label}",
                label,
                f"Run the {action.replace('_', ' ')} action for {label.lower()}.",
                dangerous=action in {"delete", "publish", "archive", "refund"},
            )
        return key

    def add_view(
        self,
        view: Any,
        name: str,
        *,
        url: str | None = None,
        category: str = "Custom",
        icon: str = "fa-puzzle-piece",
        methods: set[str] | None = None,
        permission: str = "admin.view_dashboard",
    ) -> Any:
        """Register a Flask-Admin-style custom page and navigation item.

        The page is protected by ``permission`` before the callback runs. The
        callback may still perform additional object-level authorization.
        """

        route_name = url or name.lower().replace(" ", "-")
        route_path = f"{self.url_prefix}/{route_name.strip('/')}"
        async def protected_view(request: Request) -> Response:
            await self._require_user(request, permission)
            if request.method not in {"GET", "HEAD", "OPTIONS"} and not self.csrf.verify_token(request.headers.get("x-csrf-token", "")):
                raise Forbidden("CSRF token missing or invalid")
            result = view(request)
            return await result if hasattr(result, "__await__") else result

        self.app.router.route(route_path, methods=methods or {"GET"}, name=f"admin_custom_{route_name}")(protected_view)
        self.custom_views.append({"name": name, "url": route_path, "category": category, "icon": icon})
        return view

    def mount_module(
        self,
        module: Any,
        *,
        prefix: str | None = None,
        name: str | None = None,
        navigation: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Mount a normal :class:`FlaxonModule` as an Admin extension.

        The module keeps its own routes, hooks, templates, static assets and
        dependencies. Admin only supplies the mount boundary and optional
        navigation metadata, so extension code does not need to reach into
        Admin internals or query another service's database.
        """

        import flaxon.modules  # noqa: F401 - installs Flaxon.mount_module

        mount_prefix = prefix or f"{self.url_prefix}/extensions/{getattr(module, 'name', 'module')}"
        mount_name = name or f"admin.{getattr(module, 'name', 'module')}"
        self.app.mount_module(module, prefix=mount_prefix, name=mount_name)
        for item in navigation or getattr(module, "admin_navigation", []) or []:
            entry = dict(item)
            entry.setdefault("url", mount_prefix.rstrip("/") + "/" + str(entry.get("path", "")).lstrip("/"))
            entry.setdefault("category", "Extensions")
            entry.setdefault("icon", "fa-puzzle-piece")
            self.custom_views.append(entry)
        return module

    def _permission_context(self) -> dict[str, Any]:
        role_permission_keys = {
            role: sorted({self.permission_catalog.resolve(item) for item in permissions})
            for role, permissions in self.roles.items()
        }
        return {
            "permission_groups": self.permission_catalog.grouped(),
            "permission_choices": self.permission_catalog.permission_choices(),
            "role_permission_keys": role_permission_keys,
        }

    def add_hook(self, name: str, callback: Any) -> Any:
        self.hooks.setdefault(name, []).append(callback)
        return callback

    def run_hook(self, name: str, value: Any) -> Any:
        for callback in self.hooks.get(name, []):
            value = callback(value)
        return value

    def unregister(self, model: Any) -> None:
        """Unregister a model from the dashboard's registry."""
        self.registry.unregister(model)

    def navigation_user(self):
        """Current request's staff identity, including views with sparse contexts."""
        return self._navigation_user.g…13838 tokens truncated…   deleted += 1
        if self.store:
            self.store.set("media", "metadata", self.media_metadata)
        await self._persist_database()
        self.record_activity("media_bulk_deleted", "media", request, details={"count": deleted})
        return JSONResponse({"deleted": deleted})

    async def media_signed_url(self, request: Request, filename: str) -> Response:
        await self._require_user(request, "media.manage_library")
        name = "/".join(Sanitizer.sanitize_filename(part) for part in filename.split("/") if part not in {"", "."})
        exists = await self.media_storage.exists(name) if self.media_storage is not None else self.media.exists(str(self.media._safe_path(name)))
        if not exists:
            raise NotFound("Media file not found.")
        if self.media_storage is not None and hasattr(self.media_storage, "get_signed_url"):
            result = self.media_storage.get_signed_url(name, int(request.query.get("expires", "900") or 900))
            url = await result if hasattr(result, "__await__") else result
        else:
            url = self.media_storage.get_url(name) if self.media_storage is not None else self.media.get_url(str(self.media._safe_path(name)))
        return JSONResponse({"name": name, "url": url, "signed": bool(self.media_storage is not None and hasattr(self.media_storage, "get_signed_url"))})

    async def media_api(self, request: Request, filename: str) -> Response:
        await self._require_user(request, "media.manage_library")
        if not self.csrf.verify_token(request.headers.get("x-csrf-token", "")):
            raise Forbidden("CSRF token missing or invalid")
        filename = "/".join(Sanitizer.sanitize_filename(part) for part in filename.split("/") if part not in {"", "."})
        path = str(self.media._safe_path(filename))
        exists = await self.media_storage.exists(filename) if self.media_storage is not None else self.media.exists(path)
        if not exists:
            raise NotFound("Media file not found.")
        if request.method == "DELETE":
            if self.media_storage is not None:
                await self.media_storage.delete(filename)
            else:
                self.media.delete(path)
            self.media_metadata.pop(filename, None)
            if self.store:
                self.store.set("media", "metadata", self.media_metadata)
            await self._persist_database()
            return JSONResponse({"deleted": True})
        data = await request.json() or {}
        new_name = "/".join(Sanitizer.sanitize_filename(part) for part in str(data.get("name", filename)).split("/") if part not in {"", "."})
        if not new_name:
            raise BadRequest("A media filename is required.")
        if new_name != filename:
            target_exists = await self.media_storage.exists(new_name) if self.media_storage is not None else self.media.exists(str(self.media._safe_path(new_name)))
            if target_exists:
                raise BadRequest("A media file with that name already exists.")
        target = str(self.media._safe_path(new_name))
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        if self.media_storage is not None:
            await self._storage_write(new_name, await self.media_storage.read(filename), self.media_metadata.get(filename, {}).get("content_type"))
            await self.media_storage.delete(filename)
        else:
            os.replace(path, target)
        metadata = self.media_metadata.pop(filename, {})
        editable_metadata = {"alt", "title", "caption", "description", "credit"}
        for key, value in (data.get("metadata") or {}).items():
            if key in editable_metadata:
                metadata[key] = str(value).strip()[:1000]
        self.media_metadata[new_name] = metadata
        if self.store:
            self.store.set("media", "metadata", self.media_metadata)
        await self._persist_database()
        url = self.media_storage.get_url(new_name) if self.media_storage is not None else self.media.get_url(target)
        return JSONResponse({"name": new_name, "url": url, "metadata": metadata})

    async def search(self, request: Request) -> Response:
        user = await self._require_user(request, "admin.view_dashboard")
        needle = request.query.get("q", "").lower().strip()
        results = []
        if needle:
            for model in self.registry.get_all():
                for obj in await self._visible_instances(model, user):
                    values = self._safe_record(UpdateView._snapshot(obj))
                    if needle in " ".join(str(v) for v in values.values()).lower():
                        results.append({"model": model.get_name(), "label": model.get_verbose_name(), "id": values.get("id", ""), "values": values})
        return await self.jinax.render_response("admin/search.html", {"query": needle, "results": results, "models": self.registry.get_all()})

    async def model_export(self, request: Request, model_name: str) -> Response:
        await self._require_model_user(request, model_name, "read")
        admin_model = self.registry.get(model_name)
        if not admin_model:
            return await self._not_found()
        values = await self._visible_instances(admin_model, request.user)
        records = [self._safe_record(UpdateView._snapshot(value)) for value in values]
        fmt = request.query.get("format", "json").lower()
        if fmt == "csv":
            output = io.StringIO()
            fields = sorted({key for record in records for key in record})
            writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
            return Response(output.getvalue(), media_type="text/csv; charset=utf-8", headers={"content-disposition": f"attachment; filename={model_name}.csv"})
        return JSONResponse(records, headers={"content-disposition": f"attachment; filename={model_name}.json"})

    async def model_import(self, request: Request, model_name: str) -> Response:
        await self._require_model_user(request, model_name, "create")
        admin_model = self.registry.get(model_name)
        if not admin_model:
            return await self._not_found()
        form = await request.form() if "multipart/form-data" in request.headers.get("content-type", "") else None
        if form is not None:
            form_data = form.to_dict() if hasattr(form, "to_dict") else dict(form)
            self.validate_csrf(form_data)
        elif not self.csrf.verify_token(request.headers.get("x-csrf-token", "")):
            raise Forbidden("CSRF token missing or invalid")
        raw = next((value for value in form.get_all().values() if hasattr(value, "filename")), None) if form else None
        if raw is not None:
            payload = (await raw.read()).decode("utf-8")
            fmt = "csv" if str(raw.filename).lower().endswith(".csv") else "json"
        else:
            payload = await request.text()
            fmt = "csv" if "csv" in request.headers.get("content-type", "") else "json"
        try:
            records = list(csv.DictReader(io.StringIO(payload))) if fmt == "csv" else json.loads(payload)
        except (TypeError, ValueError, csv.Error) as exc:
            raise BadRequest(f"Invalid import document: {exc}") from exc
        if not isinstance(records, list):
            raise BadRequest("Import document must contain a list of records.")
        created, errors, valid = [], [], []
        for row, record in enumerate(records, 1):
            if not isinstance(record, dict):
                errors.append({"row": row, "error": "Record must be an object."})
                continue
            try:
                validator = admin_model.validate_import or getattr(admin_model.model, "validate_instance", None)
                if validator is not None:
                    checked = validator(record)
                    checked = await checked if hasattr(checked, "__await__") else checked
                    if checked is False:
                        raise ValueError("Record failed import validation.")
                valid.append((row, record))
            except Exception as exc:  # noqa: BLE001
                errors.append({"row": row, "error": str(exc)})
        preview = str(request.query.get("preview", "")).lower() in {"1", "true", "yes"}
        if preview:
            return JSONResponse({"valid": len(valid), "errors": errors, "rows": [row for row, _ in valid]})
        allow_partial = str(request.query.get("allow_partial", "")).lower() in {"1", "true", "yes"}
        if errors and not allow_partial:
            return JSONResponse({"imported": 0, "errors": errors, "rolled_back": True}, status_code=422)
        created_records: list[dict[str, Any]] = []
        try:
            for row, record in valid:
                result = admin_model.model.create_instance(record) if hasattr(admin_model.model, "create_instance") else None
                result = await result if hasattr(result, "__await__") else result
                created_records.append(result or record)
            created = created_records
        except Exception as exc:  # noqa: BLE001
            if not allow_partial:
                for item in created_records:
                    identifier = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
                    delete = getattr(admin_model.model, "delete_instance", None)
                    if delete is not None and identifier is not None:
                        result = delete(identifier)
                        if hasattr(result, "__await__"):
                            await result
                errors.append({"row": "unknown", "error": str(exc)})
                return JSONResponse({"imported": 0, "errors": errors, "rolled_back": True}, status_code=422)
            errors.append({"row": "unknown", "error": str(exc)})
        self.record_activity("imported", model_name, request, details={"imported": len(created), "errors": len(errors)})
        return JSONResponse({"imported": len(created), "errors": errors}, status_code=201 if not errors else 207)

    async def settings_view(self, request: Request) -> Response:
        await self._require_user(request, "admin.manage_settings")
        if request.method == "POST":
            form = self.validate_csrf(self._form_dict(await request.form()))
            self.config.site_title = str(form.get("site_title", self.config.site_title))
            self.config.site_header = str(form.get("site_header", self.config.site_header))
            self.config.timezone = str(form.get("timezone", self.config.timezone))
            # Custom settings are opt-in. Do not persist arbitrary POST keys;
            # applications declare editable settings in AdminConfig(settings=...).
            editable = set(self.config.settings)
            self.config.settings.update({k: v for k, v in form.items() if k in editable})
            if self.store:
                self.store.set("meta", "config", self.config.to_dict())
            self.record_activity("settings_updated", "settings", request)
            await self._persist_database()
        return await self.jinax.render_response(
            "admin/settings.html",
            {
                "config": self.config,
                "models": self.registry.get_all(),
                "user": getattr(request, "user", None),
                "editable_settings": sorted(self.config.settings),
            },
        )

    async def history(self, request: Request, model_name: str, object_id: str) -> Response:
        user = await self._require_user(request, "admin.view_dashboard")
        model = self.registry.get(model_name)
        if not model:
            return await self._not_found()
        entries = [a.to_dict() for a in self.activities if a.resource == model_name and a.record_id == object_id]
        obj = None
        if hasattr(model.model, "get_instance"):
            result = model.model.get_instance(object_id)
            obj = await result if hasattr(result, "__await__") else result
        return await self.jinax.render_response(
            "admin/history.html",
            {
                "model": model,
                "object_id": object_id,
                "object": obj,
                "entries": entries[::-1],
                "models": self.registry.get_all(),
                "user": user,
                "can_change": self.can_access_model(user, model_name, "update"),
                "can_delete": self.can_access_model(user, model_name, "delete"),
            },
        )

    async def activity_view(self, request: Request) -> Response:
        user = await self._require_user(request, "admin.view_dashboard")
        query = request.query.get("q", "").lower().strip()
        action = request.query.get("action", "").lower().strip()
        resource = request.query.get("resource", "").lower().strip()
        actor = request.query.get("username", "").lower().strip()
        entries = []
        for item in self.activities:
            value = item.to_dict()
            if query and query not in f"{item.action} {item.resource} {item.username} {item.record_id or ''}".lower():
                continue
            if action and item.action.lower() != action:
                continue
            if resource and item.resource.lower() != resource:
                continue
            if actor and item.username.lower() != actor:
                continue
            entries.append(value)
        return await self.jinax.render_response(
            "admin/activity.html",
            {
                "entries": entries[::-1],
                "models": self.registry.get_all(),
                "user": user,
                "request": request,
                "activity_actions": sorted({item.action for item in self.activities}),
                "activity_resources": sorted({item.resource for item in self.activities}),
                "activity_users": sorted({item.username for item in self.activities}),
                "activity_total": len(entries),
            },
        )

    async def activity_export(self, request: Request) -> Response:
        await self._require_user(request, "admin.view_dashboard")
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["action", "resource", "record_id", "username", "timestamp", "details"])
        writer.writeheader()
        for item in reversed(self.activities):
            writer.writerow(item.to_dict())
        return Response(output.getvalue(), media_type="text/csv; charset=utf-8", headers={"content-disposition": "attachment; filename=flaxon-activity.csv"})

    async def notifications_api(self, request: Request) -> Response:
        """Return and update durable per-user admin notifications."""
        user = await self._require_user(request, "admin.view_dashboard")
        username = getattr(user, "username", "system")
        if request.method == "POST":
            if not self.csrf.verify_token(request.headers.get("x-csrf-token", "")):
                raise Forbidden("CSRF token missing or invalid")
            body = await request.json() or {}
            ids = body.get("ids")
            if body.get("all"):
                ids = [item["id"] for item in self.notifications]
            if not isinstance(ids, list):
                raise BadRequest("Notification ids must be a list.")
            selected = {str(item) for item in ids}
            for item in self.notifications:
                if item.get("id") in selected and username not in item.setdefault("read_by", []):
                    item["read_by"].append(username)
            if self.notification_service is not None:
                self.notification_service.mark_read(username, [str(item) for item in ids], all_messages=bool(body.get("all")))
            if self.store:
                self.store.set("meta", "notifications", self.notifications[-1000:])
            await self._persist_database()
        if self.notification_service is not None:
            entries = []
            for message in self.notification_service.list(username, unread_only=True, limit=20):
                payload = message.get("payload") or {}
                entries.append({**payload, "id": message.get("id"), "username": username, "timestamp": message.get("created_at"), "delivery_status": message.get("delivery_status")})
        else:
            entries = [item for item in self.notifications[::-1] if username not in item.get("read_by", [])][:20]
        return JSONResponse({
            "items": entries,
            "unread": len(entries),
        })

    async def notification_preferences(self, request: Request) -> Response:
        user = await self._require_user(request, "admin.view_dashboard")
        if self.notification_service is None:
            raise BadRequest("Notification preferences require persistent AdminStore storage.")
        username = str(user.username)
        if request.method == "POST":
            if not self.csrf.verify_token(request.headers.get("x-csrf-token", "")):
                raise Forbidden("CSRF token missing or invalid")
            self.notification_service.set_preferences(username, await request.json() or {})
        return JSONResponse(self.notification_service.preferences(username))

    async def audit_verify(self, request: Request) -> Response:
        await self._require_user(request, "admin.view_dashboard")
        return JSONResponse({"valid": self.audit_log.verify() if self.audit_log else False})

    async def webauthn_api(self, request: Request) -> Response:
        user = await self._require_user(request, "admin.manage_profile")
        if self.webauthn is None:
            raise BadRequest("WebAuthn requires persistent AdminStore storage.")
        if not self.csrf.verify_token(request.headers.get("x-csrf-token", "")):
            raise Forbidden("CSRF token missing or invalid")
        data = await request.json() or {}
        operation = request.path.rsplit("/", 1)[-1]
        if operation == "begin":
            result = self.webauthn.begin_registration(user.username) if "/register/" in request.path else self.webauthn.begin_authentication(user.username)
        elif "/register/" in request.path:
            result = self.webauthn.finish_registration(user.username, data)
        else:
            result = self.webauthn.finish_authentication(user.username, data)
        if hasattr(result, "__await__"):
            result = await result
        return JSONResponse({"result": result})

    async def trusted_devices_api(self, request: Request, device_id: str | None = None) -> Response:
        user = await self._require_user(request, "admin.manage_profile")
        if request.method != "GET" and not self.csrf.verify_token(request.headers.get("x-csrf-token", "")):
            raise Forbidden("CSRF token missing or invalid")
        if request.method == "GET":
            return JSONResponse({"items": self.auth.list_trusted_devices(user.username)})
        if request.method == "DELETE":
            return JSONResponse({"revoked": self.auth.revoke_trusted_device(user.username, str(device_id or ""))})
        body = await request.json() or {}
        token = self.auth.issue_trusted_device(user.username, str(body.get("label", "Browser")))
        await self._persist_database()
        return JSONResponse({"token": token}, status_code=201)

    async def mfa_recovery_api(self, request: Request) -> Response:
        user = await self._require_user(request, "admin.manage_profile")
        if not self.csrf.verify_token(request.headers.get("x-csrf-token", "")):
            raise Forbidden("CSRF token missing or invalid")
        body = await request.json() or {}
        codes = self.auth.regenerate_mfa_recovery_codes(user.username, int(body.get("count", 10)))
        await self._persist_database()
        return JSONResponse({"codes": codes})

    async def operations_view(self, request: Request) -> Response:
        user = await self._require_user(request, "admin.view_dashboard")
        health = getattr(self.app, "health", None)
        checks = []
        if health is not None and hasattr(health, "checks"):
            checks = [{"name": name, "status": getattr(check, "status", "registered")} for name, check in getattr(health, "checks", {}).items()]
            self._record_operation("health", {"checks": checks})
        metrics = getattr(self.app, "metrics", None)
        tasks = await self._task_snapshots()
        failed_tasks = [item for item in tasks if item.get("status") in {"failed", "timeout"}]
        check_statuses = [str(item.get("status", "registered")).lower() for item in checks]
        operation_kinds = {}
        for operation in self.operations:
            kind = str(operation.get("kind", "operation"))
            operation_kinds[kind] = operation_kinds.get(kind, 0) + 1
        operation_summary = {
            "checks": len(checks),
            "healthy_checks": sum(status in {"ok", "healthy", "registered"} for status in check_statuses),
            "failed_tasks": len(failed_tasks),
            "operations": len(self.operations),
            "operation_kinds": operation_kinds,
        }
        return await self.jinax.render_response(
            "admin/operations.html",
            {
                "checks": checks,
                "metrics": metrics,
                "tasks": tasks,
                "failed_tasks": failed_tasks,
                "operations": self.operations[-100:][::-1],
                "operation_summary": operation_summary,
                "models": self.registry.get_all(),
                "user": user,
            },
        )

    async def operations_tasks_api(self, request: Request) -> Response:
        await self._require_user(request, "admin.view_dashboard")
        return JSONResponse({"tasks": await self._task_snapshots()})

    async def _task_snapshots(self) -> list[dict[str, Any]]:
        queue = getattr(self.app, "task_queue", None) or getattr(self.app, "tasks", None)
        if queue is None or not hasattr(queue, "get_all_tasks"):
            return []
        tasks = await queue.get_all_tasks()
        snapshots = [{"id": task.id, "name": task.name, "status": getattr(task.status, "value", str(task.status)), "error": task.error, "queue": task.queue, "created_at": task.created_at.isoformat()} for task in tasks]
        failures = [item for item in snapshots if item["status"] in {"failed", "timeout"}]
        if failures:
            self._record_operation("task_failure", {"tasks": failures})
        return snapshots

    def _record_operation(self, kind: str, payload: dict[str, Any]) -> None:
        record = {"id": secrets.token_hex(8), "kind": kind, "timestamp": time.time(), **payload}
        self.operations.append(record)
        self.operations = self.operations[-1000:]
        if self.store and hasattr(self.store, "record_operation"):
            self.store.record_operation(kind, payload, record["id"])
        elif self.store:
            self.store.set("operations", "records", self.operations)

    def get_urls(self) -> list[tuple[str, str, Any]]:
        return [
            (f"{self.url_prefix}/", "GET", self.index),
            (f"{self.url_prefix}/<model_name>", "GET", self.list_view),
            (f"{self.url_prefix}/<model_name>/add", "GET", self.add_view),
            (f"{self.url_prefix}/<model_name>/add", "POST", self.add_view),
            (f"{self.url_prefix}/<model_name>/<object_id>", "GET", self.detail_view),
            (f"{self.url_prefix}/<model_name>/<object_id>/edit", "GET", self.edit_view),
            (f"{self.url_prefix}/<model_name>/<object_id>/edit", "POST", self.edit_view),
            (f"{self.url_prefix}/<model_name>/<object_id>/history", "GET", self.history),
            (f"{self.url_prefix}/<model_name>/<object_id>/delete", "POST", self.delete_view),
        ]
