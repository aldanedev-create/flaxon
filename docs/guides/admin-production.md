# Flaxon Admin in Production

This guide explains how to deploy, configure, extend, and operate the Flaxon
Admin dashboard. The Admin is a server-rendered management surface for
application models and administrative operations. It is not a replacement for
your application database, identity provider, mail service, object storage,
job worker, or monitoring platform.

For the CMS SPA and publishing features, see [Admin and CMS Production
Guide](admin-cms.md). For endpoint details, see the [Admin API
reference](../api/admin.md).

## What the Admin Provides

The built-in dashboard includes:

- Cookie-backed login and logout
- Password policy validation, password reset tokens, and optional email verification
- TOTP authenticator-app MFA with recovery codes
- User creation, editing, deactivation, deletion, and role assignment
- Role and permission editing with protected system roles
- Registered-model list, detail, create, edit, delete, search, filters, sorting, and pagination
- Permission-aware model actions and bulk actions
- Global model search
- Media upload, metadata, folders, validation, hashing, thumbnails, and custom storage adapters
- Settings persistence
- Activity history, hash-chained audit verification, notifications, and operations views
- CSV/JSON model export and import endpoints
- CSRF-protected browser forms and SPA mutations
- Optional Redis sessions, distributed rate limits, Redis WebSocket broadcasting, and publishing locks

Several production capabilities are extension points rather than bundled
services. Email delivery, WebAuthn verification, antivirus scanning, durable
workers, scheduler execution, object storage credentials, and alert delivery
must be configured by the application.

## Installation and Bootstrap

Install the framework with the dependencies required by the deployment:

```bash
python -m pip install "flaxon[standard]"
```

Create the application and an Admin instance. Use a strong password from an
environment variable or a secret manager; the literal value below is only a
local example.

```python
import os

from flaxon import Flaxon
from flaxon.admin import AdminConfig, AdminDashboard

app = Flaxon("backoffice", debug=False)

admin = AdminDashboard(
    app,
    url_prefix="/admin",
    config=AdminConfig(
        site_title="Acme Operations",
        site_header="Acme Operations",
        index_title="Operations dashboard",
        timezone="UTC",
    ),
    storage_path="var/admin.sqlite3",
    users=[{
        "username": "owner",
        "password": os.environ["FLAXON_ADMIN_PASSWORD"],
        "email": "owner@example.com",
        "roles": ["administrator"],
    }],
)
```

Run locally:

```bash
flaxon run app:app --reload --port 8000
```

Open `/admin/login`. The dashboard is mounted at `/admin/` and the model
interface uses `/admin/<model-name>`.

## Persistence and Migrations

`storage_path` enables the built-in SQLite AdminStore. For PostgreSQL or Neon,
use `PostgreSQLAdminStore(database_url)` and pass it as `store`; it persists
the same auxiliary Admin state without a local filesystem dependency. Both
stores persist Admin users,
roles, settings, sessions, reset/verification tokens, activities, media
metadata, notifications, operations, jobs, audit entries, uploads, and CMS
namespaces. Create the parent directory before startup.

For an application-owned database, generate the migration files and apply them
with the Flaxon CLI:

```python
from flaxon.admin import write_admin_migration

write_admin_migration("migrations")
```

```bash
flaxon migrate --database sqlite://./var/app.sqlite3 --migrations-dir migrations
```

Pass the configured `DatabaseManager` as `database=` to the Admin and CMS.
Run migrations before starting web processes and workers. For multiple
workers, use a database-backed session backend or configure Redis sessions;
the default in-memory session backend is process-local.

## Sessions and Redis

Redis is recommended when more than one web process handles Admin requests:

```python
admin = AdminDashboard(
    app,
    storage_path="var/admin.sqlite3",
    redis_url=os.environ["REDIS_URL"],
    redis_protocol=2,
    redis_max_connections=100,
    session_idle_timeout=1800,
)
```

Redis settings apply to Admin sessions, Admin request rate limits, publishing
locks, and optional WebSocket broadcasting. Configure Redis with authentication
and TLS in production. Use `redis_protocol=3` only when the installed Redis
client and server are tested together; RESP2 is the conservative default.

## Authentication, Passwords, and MFA

The login form requires username and password. The authenticator field is an
additional six-digit TOTP factor when `mfa_secret` is enabled for the account.
Users enroll from `/admin/profile`; the setup flow displays a QR code, requires
confirmation with a current code, and generates one-time recovery codes.

```python
admin = AdminDashboard(
    app,
    users=[{
        "username": "owner",
        "password": os.environ["FLAXON_ADMIN_PASSWORD"],
        "email": "owner@example.com",
        "roles": ["administrator"],
        # Use a secret provisioned by a secret manager for pre-enrolled MFA.
        "mfa_secret": os.environ.get("FLAXON_ADMIN_MFA_SECRET"),
    }],
)
```

Do not log MFA secrets or recovery codes. Password creation and change flows
use `PasswordValidator`; reset passwords are also validated. Reset and email
verification tokens are single-use and expire, but delivery still requires an
application callback:

```python
async def send_reset(identifier: str, token: str) -> None:
    await mail.send(
        to=identifier,
        subject="Reset your Admin password",
        body=f"https://admin.example.com/admin/password-reset?token={token}",
    )


async def send_verification(email: str, token: str) -> None:
    await mail.send(
        to=email,
        subject="Verify your Admin email",
        body=f"https://admin.example.com/admin/verify-email?token={token}",
    )


admin = AdminDashboard(
    app,
    password_reset_sender=send_reset,
    email_verification_sender=send_verification,
    require_email_verification=True,
)
```

The callbacks should enqueue mail rather than block a request on a remote mail
provider. Configure distributed rate limiting with Redis for password reset and
MFA endpoints when multiple workers are used.

## Users, Roles, and Permissions

The Admin UI exposes user and role management to users with `admin:users`.
Use least privilege and keep the protected `staff` and `administrator` roles.
Model permissions follow `<model>:<action>`:

```text
admin:read          dashboard and read-only access
admin:write         general writes and fallback model writes
admin:users         users and roles
admin:media         media operations
admin:settings      settings writes
admin:superuser     full access
flower:read         read Flower records
flower:create       create Flower records
flower:update       update Flower records
flower:delete       delete Flower records
```

The server enforces permissions at route boundaries. UI controls are a
convenience only; custom clients must handle `401` and `403` responses and must
not rely on hidden buttons as authorization.

## Registering Models

The model must expose asynchronous or synchronous `get_instances`,
`get_instance`, `create_instance`, `update_instance`, and
`delete_instance` methods. Register list behavior with `admin_model`:

```python
from flaxon.admin import admin_model


@admin_model(
    list_display=["id", "name", "price", "active"],
    search_fields=["name", "sku"],
    list_filter=["active", "category"],
    fields=["name", "sku", "price", "active", "category"],
    readonly_fields=["id"],
    ordering=["name"],
)
class Flower:
    _items = {}
    _next_id = 1

    @classmethod
    async def get_instances(cls):
        return list(cls._items.values())

    @classmethod
    async def get_instance(cls, object_id):
        return cls._items.get(str(object_id))

    @classmethod
    async def create_instance(cls, data):
        object_id = str(cls._next_id)
        cls._next_id += 1
        cls._items[object_id] = {"id": object_id, **data}
        return cls._items[object_id]

    @classmethod
    async def update_instance(cls, object_id, data):
        item = cls._items.get(str(object_id))
        if item is None:
            return None
        item.update(data)
        return item

    @classmethod
    async def delete_instance(cls, object_id):
        return cls._items.pop(str(object_id), None) is not None
```

Alternatively register explicitly with `admin.register(Model, ...)`. The
decorator uses the default registry, so register models before constructing
the dashboard or pass the model to the dashboard registry as appropriate for
the application.

## Lists, Search, Filters, Sorting, and Bulk Actions

The model list supports:

- `q` search across `search_fields` (or configured fields)
- `filter_<field>` exact-value filters for `list_filter`
- `order_by=<field>` and `order_by=-<field>` sorting
- `page` and `per_page` pagination, capped at 200 per page
- Checkbox selection and registered bulk actions

Example URLs:

```text
/admin/flower?q=rose
/admin/flower?filter_category=Bouquets&order_by=-price
/admin/flower?q=rose&filter_active=True&page=2&per_page=50
```

For models backed by `get_instances`, Flaxon performs these controls in the
Admin view. For models that expose a custom `query()` method, pass filtering,
ordering, and pagination through that method in the model implementation.

Register a bulk action:

```python
async def restock(ids):
    for object_id in ids:
        flower = await Flower.get_instance(object_id)
        if flower:
            await Flower.update_instance(object_id, {
                "stock": int(flower.get("stock", 0)) + 10,
            })


admin.registry.get("flower").add_action("restock", restock)
```

Bulk forms include CSRF tokens and the action route enforces model/action
permissions. Keep actions idempotent where possible and wrap multi-record
database writes in one transaction in your repository.

## Custom Columns and Display Logic

Keep list fields cheap and deterministic. For expensive derived values, add a
stored field or a query annotation rather than doing network requests during
template rendering. Custom display decorators are available for project
specific display methods; ensure the method is safe for untrusted values.

## Media

The Admin media page supports upload, folders, metadata, content hashing,
allowed MIME types, maximum size checks, image validation, dimensions, and
thumbnail scheduling. Configure a storage adapter for object storage:

```python
from flaxon.files.adapters.s3 import S3StorageAdapter

media = S3StorageAdapter(
    bucket=os.environ["MEDIA_BUCKET"],
    region=os.environ.get("AWS_REGION", "us-east-1"),
    endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
)

admin = AdminDashboard(
    app,
    media_storage=media,
    allowed_upload_types={"image/jpeg", "image/png", "image/webp", "application/pdf"},
    max_upload_size=20 * 1024 * 1024,
    media_scanner=scan_with_antivirus,
)
```

For production uploads, provide an antivirus scanner, strip EXIF data where
required, use signed URLs for private objects, and run thumbnail work through a
durable worker. Do not make private media publicly readable merely to simplify
the Admin preview.

## Settings, Activity, Audit, and Operations

The settings page persists `AdminConfig` values and application settings. Give
`admin:settings` only to operators who need it. Activity records are useful for
the UI; the hash-chained audit service provides tamper-evident verification at
`GET /admin/audit/verify`. Store audit data in a database with restricted write
access and define a retention policy before deployment.

The operations page exposes health checks, task records, and recent failures.
Register application-specific health checks and send serious failures to the
normal observability stack; the Admin page is not an alerting system.

Notifications are persisted and can be marked read. Delivery to email, SMS,
push, or an external event bus is application-specific. Configure notification
preferences and use Redis/WebSockets when cross-worker real-time fanout is
required.

## CSRF Requirements

All browser forms must include:

```html
<input type="hidden" name="_csrf" value="{{ dashboard.csrf_token() }}">
```

All JSON mutations must send:

```http
X-CSRF-Token: <token rendered by the Admin page>
```

The Admin list bulk action, delete forms, settings, profile, users, roles,
media, notifications, and CMS SPA mutations follow this rule. Never disable
CSRF validation to make a custom form work; inspect the rendered token and
request headers instead.

## Adding a Custom Admin Page

Custom pages can be mounted on the same application router. Authenticate and
authorize inside the handler, then use the Admin Jinax instance to render a
template:

```python
from flaxon.http import HTMLResponse


@app.get("/admin/reports", name="admin_reports")
async def reports(request) -> HTMLResponse:
    user = await admin.auth.current_user(request)
    admin.auth.authorize(user, "admin:read")
    report = await build_report()
    return await admin.jinax.render_response(
        "admin/reports.html",
        {
            "dashboard": admin,
            "models": admin.registry.get_all(),
            "report": report,
        },
    )
```

Place `reports.html` in the configured template directory. For a page that
should use the Admin shell, extend `admin/base.html`:

```jinja
{% extends "admin/base.html" %}
{% block title %}Reports{% endblock %}
{% block content %}
<h1 class="text-2xl font-bold">Reports</h1>
<pre>{{ report }}</pre>
{% endblock %}
```

For a JSON page, return `JSONResponse` and use the same permission checks. Add
CSRF validation to every non-read-only endpoint. Keep custom route paths
specific enough to avoid collisions with `/admin/<model_name>`.

## Custom Actions and Widgets

Register dashboard widgets for summary values that are safe to calculate on a
request. Keep slow work out of the request path by supplying a cached value:

```python
open_deliveries_count = 12  # Refresh this from a scheduled metrics task.
admin.register_widget(lambda: {
    "title": "Open deliveries",
    "value": open_deliveries_count,
})
```

Prefer cached metrics for dashboard traffic. Add custom actions to the
registered `AdminModel` and enforce the corresponding permission on the server.

## Custom Templates, CSS, and JavaScript

Use `template_dir` or a project-level Jinax loader to override templates. Keep
the required context variables used by the base shell and preserve the CSRF
fields. Add project assets under your own static prefix so they do not collide
with `/static/admin`.

```python
admin = AdminDashboard(
    app,
    template_dir="templates/admin-overrides",
)
```

Use CSS variables or scoped classes instead of changing global framework
styles. Custom JavaScript should handle loading, empty, error, and retry
states; do not treat a visual state as proof that a mutation succeeded.

## Custom Identity Backends

If your application already owns identity, inject a session backend or adapt
your identity layer to the Admin authentication contract. The backend must
support token creation, lookup, and revocation. Keep Admin authorization checks
in place even when login is delegated.

## Deployment Checklist

Before production:

- Run Admin migrations against the production database.
- Use persistent database or Redis sessions; never rely on process memory with multiple workers.
- Set strong, secret-managed passwords and enroll MFA for every administrator.
- Configure password reset and verification mail delivery through a queue.
- Set a trusted public origin and secure cookie/TLS policy at the reverse proxy.
- Configure Redis pooling and protocol compatibility when using multiple workers.
- Configure object storage, signed URLs, upload limits, antivirus, and thumbnail workers.
- Define audit retention, restricted access, and external log export.
- Add health checks, metrics, error tracking, and alerts outside the Admin UI.
- Test model permissions with both allowed and denied users.
- Test CSRF rejection and successful form/API mutations.
- Test import/export with invalid rows, large files, and rollback behavior.
- Run browser tests for login, MFA, list search/filtering, bulk actions, media, and settings.

The Admin is production-capable when these dependencies and operational
controls are configured. A default in-memory development setup should not be
described as a production deployment.

## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
