"""Microservice control-plane primitives for Flaxon Admin.

The control plane is intentionally API-first. A service owns its database and
registers a small HTTP contract with the Admin; the Admin never opens a
service's database. The built-in registry works with any AdminStore-compatible
repository, while ``RemoteModelAdapter`` lets an Admin model use a service API
without changing the existing model registry.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any, ClassVar
from urllib.parse import urlparse

from flaxon.exceptions import BadRequest, Forbidden, NotFound
from flaxon.http import JSONResponse, Request, Response
from flaxon.modules import FlaxonModule


def _now() -> float:
    return time.time()


def _slug(value: str) -> str:
    return "-".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


@dataclass
class ServiceRecord:
    """Serializable service ownership and routing metadata."""

    name: str
    display_name: str
    base_url: str = ""
    environment: str = "default"
    version: str = ""
    status: str = "unknown"
    health_url: str = "/health/ready"
    openapi_url: str = "/openapi.json"
    tags: list[str] = field(default_factory=list)
    owner: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "name": self.name, "display_name": self.display_name}


class ServiceRegistry:
    """Atomic persistent catalog for services, instances and dependencies."""

    def __init__(self, store: Any | None = None, namespace: str = "control_plane") -> None:
        self.store = store
        self.namespace = namespace
        self._lock = threading.RLock()
        self._memory: dict[str, Any] = {"services": {}, "instances": {}, "dependencies": []}

    def _get(self, key: str, default: Any) -> Any:
        if self.store is not None:
            return self.store.get(self.namespace, key, default)
        with self._lock:
            return self._memory.get(key, default)

    def _set(self, key: str, value: Any) -> None:
        if self.store is not None:
            self.store.set(self.namespace, key, value)
        else:
            with self._lock:
                self._memory[key] = value

    def _mutate(self, key: str, callback: Callable[[Any], Any], default: Any) -> Any:
        if self.store is not None and hasattr(self.store, "mutate"):
            return self.store.mutate(self.namespace, key, callback, default)
        with self._lock:
            value = self._get(key, default)
            result = callback(value)
            self._set(key, value)
            return result

    def register(self, service: dict[str, Any] | ServiceRecord) -> dict[str, Any]:
        raw = service.to_dict() if isinstance(service, ServiceRecord) else dict(service)
        name = _slug(str(raw.get("name") or raw.get("display_name") or "service"))
        if not name:
            raise BadRequest("A service name is required.")
        base_url = str(raw.get("base_url", "")).strip()
        if base_url:
            parsed = urlparse(base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise BadRequest("Service base_url must use http:// or https:// and include a host.")
            raw["base_url"] = base_url.rstrip("/")
        raw.update(name=name, display_name=str(raw.get("display_name") or name), updated_at=_now())
        def save(values: dict[str, Any]) -> dict[str, Any]:
            values[name] = raw
            return values
        current = self._mutate("services", save, {})
        return dict(current.get(name, raw))

    def unregister(self, name: str) -> bool:
        def remove(values: dict[str, Any]) -> bool:
            return values.pop(name, None) is not None
        return bool(self._mutate("services", remove, {}))

    def get(self, name: str) -> dict[str, Any] | None:
        value = self._get("services", {}).get(name)
        return dict(value) if isinstance(value, dict) else None

    def list(self) -> list[dict[str, Any]]:
        values = self._get("services", {})
        return sorted((dict(item) for item in values.values()), key=lambda item: item.get("name", ""))

    def set_instance(self, service: str, instance: dict[str, Any]) -> dict[str, Any]:
        raw = dict(instance)
        instance_id = str(raw.get("id") or secrets.token_hex(8))
        raw.update(id=instance_id, service=service, updated_at=_now())
        def save(values: dict[str, Any]) -> dict[str, Any]:
            values[instance_id] = raw
            return values
        self._mutate("instances", save, {})
        return raw

    def instances(self, service: str | None = None) -> list[dict[str, Any]]:
        values = self._get("instances", {})
        result = [dict(item) for item in values.values()]
        return [item for item in result if service is None or item.get("service") == service]

    def set_dependencies(self, service: str, dependencies: list[str]) -> list[dict[str, str]]:
        def replace(values: list[dict[str, str]]) -> list[dict[str, str]]:
            values[:] = [item for item in values if item.get("service") != service]
            values.extend({"service": service, "depends_on": name} for name in dependencies)
            return values
        return list(self._mutate("dependencies", replace, []))

    def dependencies(self, service: str | None = None) -> list[dict[str, str]]:
        values = self._get("dependencies", [])
        return [dict(item) for item in values if service is None or item.get("service") == service]


class ServiceTokenManager:
    """One-time-display service/API keys with hashed persistent storage."""

    def __init__(self, store: Any | None = None) -> None:
        self.store = store
        self.namespace = "control_plane_security"
        self._memory: dict[str, dict[str, Any]] = {}

    def issue(self, subject: str, scopes: list[str] | None = None, *, label: str = "") -> tuple[str, dict[str, Any]]:
        token = "fxs_" + secrets.token_urlsafe(32)
        record = {"id": secrets.token_hex(8), "subject": subject, "label": label, "scopes": scopes or [], "created_at": _now(), "last_used_at": None}
        records = self.store.get(self.namespace, "tokens", {}) if self.store else self._memory
        records = dict(records or {})
        records[self.digest(token)] = record
        if self.store:
            self.store.set(self.namespace, "tokens", records)
        else:
            self._memory = records
        return token, record

    @staticmethod
    def digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def verify(self, token: str, scope: str | None = None) -> dict[str, Any] | None:
        records = self.store.get(self.namespace, "tokens", {}) if self.store else self._memory
        record = records.get(self.digest(token)) if isinstance(records, dict) else None
        if not isinstance(record, dict) or (scope and scope not in record.get("scopes", [])):
            return None
        record["last_used_at"] = _now()
        if self.store:
            self.store.set(self.namespace, "tokens", records)
        return record

    def list(self) -> list[dict[str, Any]]:
        records = self.store.get(self.namespace, "tokens", {}) if self.store else self._memory
        return [{"token_id": key[:16], **value} for key, value in (records or {}).items()]

    def revoke(self, token_id: str) -> bool:
        records = self.store.get(self.namespace, "tokens", {}) if self.store else self._memory
        key = next((key for key, value in (records or {}).items() if key.startswith(token_id) or value.get("id") == token_id), None)
        if key is None:
            return False
        records.pop(key, None)
        if self.store:
            self.store.set(self.namespace, "tokens", records)
        else:
            self._memory = records
        return True


class EventBus:
    """Small event-bus contract with a durable outbox-compatible fallback."""

    def __init__(self, store: Any | None = None) -> None:
        self.store = store
        self.namespace = "control_plane_events"
        self._memory: list[dict[str, Any]] = []

    def publish(self, topic: str, payload: dict[str, Any], *, event_id: str | None = None) -> dict[str, Any]:
        event = {"id": event_id or secrets.token_hex(12), "topic": topic, "payload": payload, "created_at": _now(), "status": "pending"}
        if self.store and hasattr(self.store, "mutate"):
            def append(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
                values.append(event)
                del values[:-5000]
                return values
            self.store.mutate(self.namespace, "outbox", append, [])
        elif self.store:
            values = self.store.get(self.namespace, "outbox", []) or []
            self.store.set(self.namespace, "outbox", (values + [event])[-5000:])
        else:
            self._memory.append(event)
            self._memory = self._memory[-5000:]
        return event

    def list(self, topic: str | None = None) -> list[dict[str, Any]]:
        events = self.store.get(self.namespace, "outbox", []) if self.store else self._memory
        result = list(events or [])
        if topic:
            result = [item for item in result if item.get("topic") == topic]
        return list(reversed(result))


class RemoteServiceError(RuntimeError):
    """A remote service request failed after retry/circuit-breaker handling."""


class RemoteServiceClient:
    """Dependency-free JSON client for service-owned APIs.

    It uses standard-library HTTP so the Admin does not require a second web
    framework or client package. Applications can subclass it for mTLS or
    replace it with their preferred async HTTP transport.
    """

    def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 5.0, retries: int = 2) -> None:
        self.base_url = base_url.rstrip("/")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Remote service URLs must use http:// or https:// and include a host.")
        self.token = token
        self.timeout = max(0.1, timeout)
        self.retries = max(0, retries)
        self._failures = 0
        self._open_until = 0.0

    async def request(self, method: str, path: str = "/", *, body: Any = None, headers: dict[str, str] | None = None) -> Any:
        if self._open_until > _now():
            raise RemoteServiceError("Remote service circuit is open.")
        url = self.base_url + (path if path.startswith("/") else "/" + path)
        request_headers = {"accept": "application/json", **(headers or {})}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            request_headers.setdefault("content-type", "application/json")
        if self.token:
            request_headers.setdefault("authorization", f"Bearer {self.token}")

        def send() -> Any:
            request = urllib.request.Request(url, data=data, headers=request_headers, method=method.upper())
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))

        error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                result = await asyncio.to_thread(send)
                self._failures = 0
                return result
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
                error = exc
                if attempt < self.retries:
                    await asyncio.sleep(0.1 * (attempt + 1))
        self._failures += 1
        if self._failures >= 3:
            self._open_until = _now() + 10
        raise RemoteServiceError(f"Request to {url} failed: {error}") from error

    async def get(self, path: str = "/") -> Any:
        return await self.request("GET", path)

    async def post(self, path: str, body: Any = None) -> Any:
        return await self.request("POST", path, body=body)

    async def patch(self, path: str, body: Any = None) -> Any:
        return await self.request("PATCH", path, body=body)

    async def delete(self, path: str) -> Any:
        return await self.request("DELETE", path)


class RemoteModelAdapter:
    """Model-shaped adapter for Admin registry entries backed by a service."""

    def __init__(self, client: RemoteServiceClient, resource: str) -> None:
        self.client = client
        self.resource = resource.strip("/")

    async def get_instances(self) -> list[dict[str, Any]]:
        payload = await self.client.get(f"/{self.resource}")
        return payload.get("items", payload) if isinstance(payload, dict) else payload

    async def get_instance(self, object_id: str) -> dict[str, Any] | None:
        return await self.client.get(f"/{self.resource}/{object_id}")

    async def create_instance(self, data: dict[str, Any]) -> Any:
        return await self.client.post(f"/{self.resource}", data)

    async def update_instance(self, object_id: str, data: dict[str, Any]) -> Any:
        return await self.client.patch(f"/{self.resource}/{object_id}", data)

    async def delete_instance(self, object_id: str) -> Any:
        return await self.client.delete(f"/{self.resource}/{object_id}")


class AdminControlPlane:
    """Admin pages and APIs for service-owned microservice deployments."""

    PAGE_SECTIONS: ClassVar[dict[str, tuple[str, str]]] = {
        "services": ("Service catalog", "Register and monitor service-owned APIs."),
        "instances": ("Service instances", "Inspect discovered service instances."),
        "service-accounts": ("Service accounts", "Issue scoped credentials for service-to-service calls."),
        "health": ("Fleet health", "Read service health and readiness status."),
        "metrics": ("Fleet metrics", "Review metrics endpoints and collection state."),
        "logs": ("Central logs", "Search log streams forwarded by services."),
        "traces": ("Distributed traces", "Inspect request IDs and trace links."),
        "alerts": ("Alerts", "Review active service and workflow alerts."),
        "alerts/rules": ("Alert rules", "Manage alert policy definitions."),
        "queues": ("Queues", "Review workers and pending jobs."),
        "queues/dead": ("Dead letters", "Retry or inspect failed events."),
        "schedules": ("Schedules", "Review distributed scheduler state."),
        "events": ("Event outbox", "Inspect published and pending integration events."),
        "config": ("Configuration", "View service configuration references."),
        "secrets": ("Secrets", "Manage secret references without exposing values."),
        "flags": ("Feature flags", "Manage rollout flags per environment."),
        "deployments": ("Deployments", "Track releases and rollback references."),
        "environments": ("Environments", "Manage development, staging and production targets."),
        "maintenance": ("Maintenance", "Coordinate maintenance windows."),
        "api-keys": ("API keys", "Review scoped API credentials."),
        "permissions": ("Permission matrix", "Review service and resource access policies."),
        "sessions": ("Sessions", "Review and revoke Admin sessions."),
        "security": ("Security center", "Review authentication and service security posture."),
        "audit": ("Audit log", "Review immutable Admin and service events."),
        "rate-limits": ("Rate limits", "Review configured request budgets."),
        "webhooks": ("Webhooks", "Manage signed outbound integrations."),
        "migrations": ("Migrations", "Track per-service schema migrations."),
        "databases": ("Databases", "Review service database ownership, never contents."),
        "cache": ("Cache", "Review cache providers and invalidation state."),
        "storage": ("Storage", "Review object storage providers and buckets."),
        "backups": ("Backups", "Track backup jobs and restore points."),
        "transfers": ("Transfers", "Track data transfer and import/export jobs."),
        "status": ("Control-plane status", "Review Admin control-plane readiness."),
        "api-docs": ("Service API docs", "Open service OpenAPI documents."),
    }

    PERMISSIONS: ClassVar[dict[str, tuple[str, str, str]]] = {
        "admin.manage_services": ("Manage services", "Service management", "Register services and instances."),
        "admin.view_fleet": ("View fleet operations", "Operations", "Read health, metrics, logs and queues."),
        "admin.manage_releases": ("Manage releases", "Operations", "Manage deployments, flags and maintenance."),
        "admin.manage_security": ("Manage security", "Security", "Manage service accounts, keys and access."),
        "admin.manage_platform": ("Manage platform", "Platform", "Manage storage, backups and migrations."),
        "admin.view_audit": ("View audit log", "Security", "Review cross-service audit events."),
    }
    PERSISTED_COLLECTIONS: ClassVar[set[str]] = {
        "config", "secrets", "flags", "deployments", "environments", "maintenance",
        "alerts", "alerts-rules", "logs", "traces", "webhooks", "rate-limits",
        "migrations", "databases", "cache", "storage", "backups", "transfers", "permissions",
    }

    def __init__(self, dashboard: Any) -> None:
        self.dashboard = dashboard
        self.app = dashboard.app
        self.url_prefix = dashboard.url_prefix
        self.registry = ServiceRegistry(dashboard.store)
        self.tokens = ServiceTokenManager(dashboard.store)
        self.events = EventBus(dashboard.store)
        self._register_permissions()
        self._register_routes()

    def _register_permissions(self) -> None:
        for key, (label, category, description) in self.PERMISSIONS.items():
            self.dashboard.register_permission(key, label, category, description, dangerous=key != "admin.view_fleet")

    def _register_routes(self) -> None:
        router = self.app.router
        page_methods = {"GET"}
        for section in self.PAGE_SECTIONS:
            handler = self._page_handler(section)
            router.route(f"{self.url_prefix}/{section}", methods=page_methods, name=f"admin_{_slug(section)}")(handler)
        router.get(f"{self.url_prefix}/services/new")(self.new_service_page)
        router.get(f"{self.url_prefix}/services/<service_name>")(self.service_page)
        router.get(f"{self.url_prefix}/users/<username>/access")(self.access_page)
        router.route(f"{self.url_prefix}/api/control-plane/<path:resource>", methods={"GET", "POST", "PATCH", "PUT", "DELETE"}, name="admin_control_plane_api")(self.api)

    def _page_handler(self, section: str) -> Callable[..., Any]:
        async def handler(request: Request) -> Response:
            return await self.page(request, section)
        handler.__name__ = f"control_plane_{section.replace('/', '_')}_page"
        return handler

    async def _user(self, request: Request, permission: str) -> Any:
        return await self.dashboard._require_user(request, permission)

    async def page(self, request: Request, section: str) -> Response:
        permission = "admin.view_fleet"
        if section in {"services", "instances", "service-accounts"}:
            permission = "admin.manage_services"
        elif section in {"api-keys", "permissions", "sessions", "security", "webhooks", "secrets"}:
            permission = "admin.manage_security"
        elif section in {"config", "deployments", "environments", "maintenance", "flags", "alerts/rules"}:
            permission = "admin.manage_releases"
        elif section in {"migrations", "databases", "cache", "storage", "backups", "transfers"}:
            permission = "admin.manage_platform"
        elif section in {"audit"}:
            permission = "admin.view_audit"
        user = await self._user(request, permission)
        title, description = self.PAGE_SECTIONS.get(section, (section.title(), ""))
        payload = await self._snapshot_async(section)
        rows: list[dict[str, Any]] = []
        for key in ("services", "instances", "events", "jobs", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                rows.extend(item if isinstance(item, dict) else {"value": item} for item in value)
        if not rows and isinstance(payload.get("records"), dict):
            rows = [{"key": key, "value": value} for key, value in payload["records"].items()]
        return await self.dashboard.jinax.render_response("admin/control_plane.html", {
            "section": section, "page_title": title, "page_description": description,
            "control_plane": self, "snapshot": payload, "rows": rows, "models": self.dashboard.registry.get_all(), "user": user,
        })

    async def new_service_page(self, request: Request) -> Response:
        return await self.page(request, "services")

    async def service_page(self, request: Request, service_name: str) -> Response:
        user = await self._user(request, "admin.manage_services")
        service = self.registry.get(service_name)
        if service is None:
            raise NotFound("Service not found.")
        return await self.dashboard.jinax.render_response("admin/control_plane.html", {
            "section": "services", "page_title": service.get("display_name", service_name),
            "page_description": f"Service detail for {service_name}.", "control_plane": self,
            "snapshot": {"services": [service], "instances": self.registry.instances(service_name), "dependencies": self.registry.dependencies(service_name)},
            "rows": [*self.registry.instances(service_name)], "models": self.dashboard.registry.get_all(), "user": user,
        })

    async def access_page(self, request: Request, username: str) -> Response:
        await self._user(request, "admin.manage_security")
        access = {"username": username, "roles": [], "permissions": [], "sessions": []}
        record = self.dashboard.auth.users.get(username)
        if record:
            access.update({"roles": record.get("roles", []), "permissions": record.get("permissions", [])})
        return await self.dashboard.jinax.render_response("admin/control_plane.html", {
            "section": "permissions", "page_title": f"Access: {username}", "page_description": "Effective permissions for this Admin account.",
            "control_plane": self, "snapshot": access, "models": self.dashboard.registry.get_all(), "user": getattr(request, "user", None),
        })

    def _snapshot(self, section: str) -> dict[str, Any]:
        services = self.registry.list()
        if section in {"services", "health", "metrics", "api-docs"}:
            return {"services": services, "instances": self.registry.instances(), "dependencies": self.registry.dependencies()}
        if section == "instances":
            return {"instances": self.registry.instances()}
        if section == "service-accounts" or section == "api-keys":
            return {"keys": self.tokens.list()}
        if section == "events":
            return {"events": self.events.list()}
        if section in {"queues", "queues/dead", "schedules"}:
            jobs = self.dashboard.job_store.list() if self.dashboard.job_store else []
            return {"jobs": [job.to_dict() for job in jobs]}
        if section == "audit":
            entries = self.dashboard.store.get("audit", "entries", []) if self.dashboard.store and self.dashboard.audit_log else []
            return {"valid": self.dashboard.audit_log.verify() if self.dashboard.audit_log else False, "events": entries}
        if section == "sessions":
            backend = self.dashboard.auth.backend
            return {"backend": type(backend).__name__, "persistent": backend is not None}
        if section == "status":
            return {
                "ready": True,
                "services": services,
                "service_count": len(services),
                "storage": type(self.dashboard.store).__name__ if self.dashboard.store else "memory",
            }
        collection = section.replace("/", "-")
        if collection in self.PERSISTED_COLLECTIONS:
            return {"items": self._collection(collection)}
        return {"services": services, "records": self.dashboard.store.list("control_plane") if self.dashboard.store and hasattr(self.dashboard.store, "list") else {}}

    def _collection(self, name: str) -> list[dict[str, Any]]:
        if self.dashboard.store is not None:
            value = self.dashboard.store.get("control_plane", name, [])
        else:
            value = getattr(self, "_memory_collections", {}).get(name, [])
        return [dict(item) for item in value] if isinstance(value, list) else []

    def _save_collection(self, name: str, values: list[dict[str, Any]]) -> None:
        values = values[-5000:]
        if self.dashboard.store is not None:
            self.dashboard.store.set("control_plane", name, values)
        else:
            if not hasattr(self, "_memory_collections"):
                self._memory_collections: dict[str, list[dict[str, Any]]] = {}
            self._memory_collections[name] = values

    async def _snapshot_async(self, section: str) -> dict[str, Any]:
        payload = self._snapshot(section)
        if section != "health":
            return payload
        services = []
        for service in payload.get("services", []):
            current = dict(service)
            base_url = str(current.get("base_url", "")).strip()
            if base_url:
                try:
                    result = await RemoteServiceClient(base_url, timeout=1.0, retries=0).get(str(current.get("health_url", "/health/ready")))
                    current["status"] = "healthy" if not isinstance(result, dict) or str(result.get("status", "ok")).lower() in {"ok", "healthy", "ready"} else str(result.get("status"))
                    current["health"] = result
                except (RemoteServiceError, ValueError) as exc:
                    current["status"] = "down"
                    current["health_error"] = str(exc)
                self.registry.register(current)
            services.append(current)
        payload["services"] = services
        return payload

    def _resource_payload(self, resource: str) -> Any:
        if resource in {"services", "health", "metrics", "api-docs"}:
            return self._snapshot("services")
        if resource == "instances":
            return {"items": self.registry.instances()}
        if resource in {"service-accounts", "api-keys"}:
            return {"items": self.tokens.list()}
        if resource in {"events", "outbox"}:
            return {"items": self.events.list()}
        if resource in {"audit", "security"}:
            return self._snapshot("audit")
        if resource in {"jobs", "queues", "schedules"}:
            return {"items": [job.to_dict() for job in (self.dashboard.job_store.list() if self.dashboard.job_store else [])]}
        collection = resource.replace("/", "-")
        if collection in self.PERSISTED_COLLECTIONS:
            return {"items": self._collection(collection)}
        return self._snapshot(resource)

    async def api(self, request: Request, resource: str) -> Response:
        root = resource.strip("/").split("/")
        name = root[0] if root else "overview"
        if root[:2] == ["alerts", "rules"]:
            collection_name = "alerts-rules"
            collection_depth = 2
        else:
            collection_name = name
            collection_depth = 1
        detail_id = root[collection_depth] if len(root) > collection_depth else None
        permission = "admin.view_fleet"
        if name in {"services", "instances", "dependencies"}:
            permission = "admin.manage_services"
        elif name in {"api-keys", "service-accounts", "permissions", "sessions", "security", "webhooks", "secrets"}:
            permission = "admin.manage_security"
        elif name in {"config", "deployments", "flags", "environments", "maintenance", "alerts"}:
            permission = "admin.manage_releases"
        elif name in {"migrations", "databases", "cache", "storage", "backups", "transfers"}:
            permission = "admin.manage_platform"
        elif name == "audit":
            permission = "admin.view_audit"
        await self._user(request, permission)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not self.dashboard.csrf.verify_token(request.headers.get("x-csrf-token", "")):
            raise Forbidden("CSRF token missing or invalid")
        if request.method == "GET":
            if name == "overview":
                return JSONResponse(self._snapshot("status"))
            if name == "health":
                return JSONResponse(await self._snapshot_async("health"))
            if name == "services" and len(root) > 1:
                record = self.registry.get(root[1])
                if record is None:
                    raise NotFound("Service not found.")
                return JSONResponse(record)
            if collection_name in self.PERSISTED_COLLECTIONS and detail_id:
                record = next((item for item in self._collection(collection_name) if str(item.get("id")) == detail_id), None)
                if record is None:
                    raise NotFound(f"{resource} record not found.")
                return JSONResponse(record)
            return JSONResponse(self._resource_payload(collection_name))
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        body = body if isinstance(body, dict) else {}
        if name == "services":
            if detail_id:
                if request.method == "DELETE":
                    return JSONResponse({"deleted": self.registry.unregister(detail_id)})
                current = self.registry.get(detail_id)
                if current is None:
                    raise NotFound("Service not found.")
                current.update(body)
                current["name"] = detail_id
                return JSONResponse(self.registry.register(current))
            record = self.registry.register(body)
            self.events.publish("ServiceRegistered", record)
            return JSONResponse(record, status_code=201)
        if name == "dependencies" and request.method == "GET":
            return JSONResponse({"items": self.registry.dependencies()})
        if name == "instances":
            record = self.registry.set_instance(str(body.get("service", "")), body)
            return JSONResponse(record, status_code=201)
        if name == "dependencies":
            service = str(body.get("service", ""))
            return JSONResponse({"items": self.registry.set_dependencies(service, [str(item) for item in body.get("depends_on", [])])})
        if name in {"service-accounts", "api-keys"}:
            if detail_id and request.method == "DELETE":
                return JSONResponse({"deleted": self.tokens.revoke(detail_id)})
            token, record = self.tokens.issue(str(body.get("subject", "service")), [str(item) for item in body.get("scopes", [])], label=str(body.get("label", "")))
            return JSONResponse({"token": token, **record}, status_code=201)
        if name == "events":
            return JSONResponse(self.events.publish(str(body.get("topic", "CustomEvent")), body), status_code=201)
        if collection_name in self.PERSISTED_COLLECTIONS:
            values = self._collection(collection_name)
            record_id = str(body.get("id") or secrets.token_hex(10))
            if detail_id:
                target_id = detail_id
                current = next((item for item in values if str(item.get("id")) == target_id), None)
                if current is None:
                    raise NotFound(f"{resource} record not found.")
                if request.method == "DELETE":
                    values = [item for item in values if str(item.get("id")) != target_id]
                    self._save_collection(collection_name, values)
                    return JSONResponse({"deleted": True})
                current.update(body, updated_at=_now())
                self._save_collection(collection_name, values)
                return JSONResponse(current)
            if collection_name == "secrets":
                body = {key: value for key, value in body.items() if key not in {"value", "secret", "plaintext"}}
                body["has_value"] = bool(body.get("has_value", True))
            body.update(id=record_id, created_at=_now(), updated_at=_now())
            values.append(body)
            self._save_collection(collection_name, values)
            return JSONResponse(body, status_code=201)
        return JSONResponse({"accepted": True, "resource": resource, "payload": body}, status_code=202)


class AdminControlPlaneModule(FlaxonModule):
    """Module marker for extensions that add Admin control-plane features."""

    def __init__(self, name: str = "admin-control-plane", **kwargs: Any) -> None:
        super().__init__(name, **kwargs)


__all__ = [
    "AdminControlPlane", "AdminControlPlaneModule", "EventBus", "RemoteModelAdapter",
    "RemoteServiceClient", "RemoteServiceError", "ServiceRecord", "ServiceRegistry", "ServiceTokenManager",
]
