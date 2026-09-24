# Admin and CMS with microservices

Flaxon Admin can act as a control plane for services that own their own
databases. The Admin stores service metadata, credentials, operational events,
and audit data. It does **not** open a Catalog, Orders, Billing, or CMS
database directly.

```text
Browser -> Admin/CMS -> gateway -> service-owned API -> service database
                         |
                         +-> Redis, workers, event bus, object storage
```

## Register the control plane

The control plane is enabled by default. Use a persistent store in every web
worker so the registry is shared. Redis should be configured for sessions,
locks, rate limits, and cross-worker events when more than one process runs.

```python
from flaxon import Flaxon
from flaxon.admin import AdminDashboard, AdminStore

app = Flaxon("operations")
admin = AdminDashboard(
    app,
    store=AdminStore("admin.sqlite3"),
    redis_url="redis://127.0.0.1:6379/0",
    users=[{"username": "admin", "password": "use-a-secret-from-your-secret-manager", "roles": ["administrator"]}],
)
```

The production equivalent can pass `PostgreSQLAdminStore` or the project's
database-backed store. Do not use SQLite on a shared multi-worker deployment.

## Service registration API

Register only connection and ownership metadata. The service remains the
authority for records and business rules.

```python
from flaxon.testing import TestClient

client = TestClient(app)
headers = {"cookie": "session_id=<admin-session>", "x-csrf-token": admin.csrf_token()}

response = client.post(
    "/admin/api/control-plane/services",
    json_data={
        "name": "catalog",
        "display_name": "Catalog",
        "base_url": "https://catalog.internal",
        "environment": "production",
        "health_url": "/health/ready",
        "openapi_url": "/openapi.json",
        "tags": ["commerce"],
    },
    headers=headers,
)
```

Available Admin pages include `/admin/services`, `/admin/health`,
`/admin/metrics`, `/admin/logs`, `/admin/traces`, `/admin/queues`,
`/admin/events`, `/admin/deployments`, `/admin/api-keys`, `/admin/audit`,
`/admin/migrations`, `/admin/storage`, `/admin/backups`, and `/admin/status`.
The control-plane API is under `/admin/api/control-plane/`.

Mutating requests require the Admin CSRF header. Service tokens are displayed
once when created and only their hashes are persisted:

```python
created = client.post(
    "/admin/api/control-plane/service-accounts",
    json_data={"subject": "orders-worker", "scopes": ["orders.read"], "label": "Orders worker"},
    headers=headers,
)
service_token = created.json()["token"]
```

## Service-owned Admin models

Use `RemoteServiceClient` and `RemoteModelAdapter` when an Admin list should
read a service API. The adapter expects a simple JSON contract: list returns
either a list or `{"items": [...]}`, and detail/create/update/delete use the
corresponding resource endpoints.

```python
from flaxon.admin import RemoteModelAdapter, RemoteServiceClient

catalog = RemoteServiceClient(
    "https://catalog.internal",
    token=service_token,
    timeout=3,
    retries=2,
)
products = RemoteModelAdapter(catalog, "products")
admin.register(
    products,
    name="product",
    fields=["id", "name", "price", "status"],
    list_display=["id", "name", "price", "status"],
)
```

This adapter includes retry and circuit-open behavior for repeated failures.
For mTLS, custom tracing, or a non-JSON service, subclass
`RemoteServiceClient` and override `request()`.

## Flaxon modules inside Admin

Modules are the extension boundary for one service or for custom Admin pages.
They can provide routes, templates, static files, dependencies, hooks, and CLI
commands without changing the Admin implementation.

```python
from flaxon.modules import FlaxonModule

reports = FlaxonModule("reports", template_dir="reports/templates")

@reports.get("/summary")
async def summary():
    return {"service": "reports", "status": "ready"}

admin.mount_module(
    reports,
    prefix="/admin/extensions/reports",
    navigation=[{"name": "Reports", "path": "summary", "icon": "fa-chart-line"}],
)
```

The module's endpoint is now `/admin/extensions/reports/summary`. Protect
extension routes with the module's `before_request` hook or a custom Admin
page permission; mounting a module does not automatically make every route
private.

## Events and the outbox

The control plane exposes an outbox-compatible `EventBus`. Publish events
after the service transaction commits, and make consumers idempotent.

```python
event = admin.control_plane.events.publish(
    "OrderCreated",
    {"order_id": "ord_123", "tenant_id": "tenant_42"},
)
```

The built-in store is useful for development and small deployments. Production
systems should forward the outbox to Redis Streams, RabbitMQ, or Kafka and
retain a dead-letter queue. Use an idempotency key for every retried command.

## CMS boundaries

The CMS workspace exposes calendar, editorial board, review, publishing,
models, media, SEO/index state, comments, menus, references, trash,
integrations, transfers, and audit data under `/admin/cms/api/workspace/<name>`.
The CMS content API remains the owner of content records and revisions. Use
object storage for media and a worker for thumbnails and scheduled publishing.

```javascript
const response = await fetch('/admin/cms/api/workspace/review', {
  credentials: 'same-origin',
});
const reviewQueue = await response.json();
```

For a public site, expose a separate read-only content API or gateway route.
Do not make a public frontend depend on Admin cookies.

## Deployment checklist

- Give every service its own database and migration command.
- Put the gateway in front of Admin and service APIs; validate identity before routing.
- Use Redis-backed sessions, rate limits, scheduler locks, and WebSocket fanout.
- Run durable job workers separately from web processes.
- Use an outbox plus a broker for cross-service events and webhooks.
- Store uploads in S3-compatible storage with signed URLs and background scanning.
- Propagate request IDs and trace IDs through gateway, Admin, and services.
- Restrict service tokens to scopes and rotate them through a secret manager.
- Keep Admin audit records append-only and apply a documented retention policy.
- Treat the built-in service registry as an operational catalog, not a service discovery replacement.
