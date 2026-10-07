# Admin and CMS API Reference

This is the implementation-oriented API map. For setup and production
guidance, read [Admin and CMS Production Guide](../guides/admin-cms.md).

## Python APIs

```python
from flaxon.admin import (
    AdminConfig, AdminDashboard, AdminAuth, AdminStore, PostgreSQLAdminStore,
    RedisAdminSessionBackend, write_admin_migration,
)
from flaxon.admin.cms import CMS, CMSField, ContentType
```

### `AdminDashboard`

```python
AdminDashboard(
    app,
    config=None,
    url_prefix="/admin",
    template_dir=None,
    registry=None,
    users=None,
    auth_backend=None,
    upload_dir="uploads",
    store=None,
    storage_path=None,
    redis_url=None,
    database=None,
    password_reset_sender=None,
    email_verification_sender=None,
    require_email_verification=False,
    max_upload_size=10 * 1024 * 1024,
    allowed_upload_types=None,
)
```

Use exactly one AdminStore strategy for the auxiliary production services:
`storage_path` for the built-in SQLite store, or `PostgreSQLAdminStore` for a
PostgreSQL/Neon deployment. The separate `database` argument persists the
dashboard and CMS application data. `redis_url` adds shared sessions, rate
limits, publishing locks, and event broadcasting when configured.

```python
from flaxon.admin import PostgreSQLAdminStore

store = PostgreSQLAdminStore(settings.database_url)
admin = AdminDashboard(app, database=database, store=store, redis_url=settings.redis_url)
app.on_shutdown(store.close)
```

Extension methods:

- `register(model, **options)` and `unregister(model)`
- `register_widget(widget)`
- `add_hook(name, callback)` and `run_hook(name, value)`
- `csrf_token()` for custom server-rendered forms

### `CMS`

```python
CMS(app, url_prefix="/admin/cms", title="CMS", template_path=None,
    auth=None, database=None)
```

Methods:

- `register(content_type)`
- `add_hook(name, callback)`
- `run_hook(name, value)`

CMS hooks include `before_create`, `after_create`, `before_update`,
`after_update`, `before_delete`, `after_delete`, and revision restore hooks.

### `ContentType`

Important configuration fields:

```python
ContentType(
    name="post",
    fields=[CMSField("title", required=True)],
    list_display=["title", "status", "updated_at"],
    list_filter=["status"],
    search_fields=["title", "body"],
    statuses=["draft", "review", "approved", "scheduled", "published", "archived"],
    has_slug=True,
    slug_source="title",
    order_by="-updated_at",
)
```

Methods include `create`, `get`, `update`, `delete`, `query`, `stats`,
`register_action`, `history`, `compare_revisions`, and `restore`.

## HTTP Routes

`AdminDashboard` serves `/admin/`, `/admin/login`, `/admin/logout`,
`/admin/profile`, `/admin/users`, `/admin/roles`, `/admin/media`,
`/admin/settings`, `/admin/search`, `/admin/activity`,
`/admin/activity/export`, `/admin/notifications`, and `/admin/operations`.

Model routes are `/admin/<model>`, `/add`, `/<id>`, `/<id>/edit`,
`/<id>/delete`, `/<id>/history`, and `/actions/<name>`.

CMS routes are listed below. Replace `/admin/cms` with the configured prefix.

| Method | Route | Auth/CSRF | Result |
|---|---|---|---|
| GET | `/api/config` | session | Schemas |
| GET | `/api/stats` | session | Counts |
| GET | `/api/<type>/items` | session | Paginated query |
| POST | `/api/<type>/items` | session + CSRF | Create |
| GET | `/api/<type>/items/<id>` | session | Record |
| PUT | `/api/<type>/items/<id>` | session + CSRF | Update + revision |
| DELETE | `/api/<type>/items/<id>` | session + CSRF | Delete + revision |
| GET | `/api/<type>/items/<id>/history` | session | Comparisons |
| POST | `/api/<type>/items/<id>/restore/<revision>` | session + CSRF | Restore |
| POST | `/api/<type>/actions/<action>` | session + CSRF | Bulk action |
| GET | `/api/export/<type>` | session | JSON/CSV download |
| POST | `/api/import/<type>` | session + CSRF | Import and row errors |
| GET/POST | `/api/taxonomies` | session / CSRF | Taxonomy collection |
| POST/PATCH/DELETE | `/api/taxonomies/<name>` | session + CSRF | Terms |
| GET/POST | `/api/comments` | session / CSRF | Moderation queue |
| PATCH/DELETE | `/api/comments/<id>` | session + CSRF | Moderate/delete |
| GET/PUT | `/api/menus/<name>` | session / CSRF | Menu hierarchy |

## Client Contract

Send the session cookie and CSRF header:

```javascript
await fetch("/admin/cms/api/post/items", {
  method: "POST",
  credentials: "same-origin",
  headers: {
    "Content-Type": "application/json",
    "X-CSRF-Token": csrfToken,
  },
  body: JSON.stringify({ title: "Hello", status: "draft" }),
});
```

Handle `401`, `403`, `404`, `409`, `413`, and `422` explicitly. Import
responses contain `items`, `imported`, and row-level `errors`. Do not expose
password hashes, MFA secrets, reset tokens, or verification tokens to clients.

## Migration API

```python
from flaxon.admin import write_admin_migration
write_admin_migration("migrations")
```

Then run `flaxon migrate --database <url> --migrations-dir migrations` in the
same release step that deploys the application. Test both apply and rollback
in CI.

## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
