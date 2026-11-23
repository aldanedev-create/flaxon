# Filters, lenses, discovery and safety

This guide covers the Phase 4 admin surface: declarative filters, lenses, saved
views, the command palette, record duplication, the CSV import wizard,
per-resource policies and impersonation.

Everything here is additive. A resource registered with the legacy
`dashboard.register(Model, list_filter=[...])` call keeps working exactly as
before; nothing below changes those defaults.

## Filters live in the URL

A filter is a small object that knows one field and one query-string key. The
change list renders a control for each declared filter, and the state is read
back from the URL, so a filtered list can be bookmarked, shared or saved.

```python
from flaxon.admin.filters import BooleanFilter, DateRangeFilter, SelectFilter, apply_python_filters

filters = [
    SelectFilter("status", choices=["pending", "paid"], label="Status"),
    BooleanFilter("fulfilled", label="Fulfilled"),
    DateRangeFilter("created_at", label="Created"),
]

params = {"filter_status": "paid", "filter_fulfilled": "true"}
rows = [
    {"id": 1, "status": "pending", "fulfilled": True},
    {"id": 2, "status": "paid", "fulfilled": False},
    {"id": 3, "status": "paid", "fulfilled": True},
]
selected = apply_python_filters(filters, params, rows)
```

`apply_python_filters` is the in-memory path used by legacy admin models. For
ORM-backed admins the same objects produce a Tortoise `Q` via `orm_q()`, and the
filter runs in SQL.

Register them on a resource:

```python
dashboard.register(
    Order,
    fields=["reference", "status", "fulfilled"],
    filters=[
        SelectFilter("status", choices=["pending", "paid"], label="Status"),
        BooleanFilter("fulfilled", label="Fulfilled"),
    ],
)
```

## Lenses: a second index for the same resource

A lens is a named alternate list with its own query and columns. It is addressed
by `?lens=<name>` and composes with filters and saved views.

```python
from flaxon.admin.lenses import Lens

unpaid = Lens(
    "unpaid",
    label="Unpaid orders",
    columns=["reference", "amount"],
    query={"filter_status": "pending"},
)
dashboard.register(Order, fields=["reference", "amount", "status"], lenses=[unpaid])
```

An unknown lens name is a `400`, not a silent fallback.

## Saved views are per-user query strings

A saved view stores the current query string under the signed-in user's name.
Applying it redirects to the list URL, so the URL stays the single source of
truth. Another user asking for the same slug gets `404` — saved views are not
enumerable.

## Discovery: command palette and shortcuts

`Ctrl`/`Cmd`+`K` opens the palette anywhere in the admin. It searches model
names and records the current user may read (`/admin/search/palette` returns
JSON). `Esc` closes it. The palette never returns records filtered out by a
`view` policy.

## Duplicate a record

`POST /admin/<model>/<id>/duplicate` copies a record with a fresh primary key.
It requires `create` permission, a valid CSRF token, and passes the record
through the resource's `create` policy.

## CSV import wizard

The import endpoint accepts CSV or JSON. Three additions make it a wizard:

* **Column mapping** — `?mapping={"Order Ref": "reference"}` renames source
  columns before validation.
* **Dry run** — `?dry_run=1` (or `?preview=1`) validates and returns the mapped
  rows without writing anything.
* **Caps** — `AdminConfig(import_max_rows=..., import_max_bytes=...)` rejects
  oversized payloads with `413`.

```python
from flaxon.admin.importing import csv_safe, enforce_limits, map_columns

mapped, errors = map_columns([{"Order Ref": "ORD-1"}], {"Order Ref": "reference"})
enforce_limits(payload_bytes=1024, row_count=len(mapped), max_bytes=5_000_000, max_rows=5000)
safe = csv_safe("=cmd|' /C calc'!A0")
```

Every CSV export passes values through `csv_safe`, which prefixes a single quote
to cells starting with `=`, `+`, `-`, `@`, tab or carriage return.

## Per-resource policies

A policy is deny-only. Actions you do not configure fall through to the existing
permission system, so adding a policy can only tighten access.

```python
from flaxon.admin.policies import Policy

policy = Policy(
    view_any=lambda user, obj=None: True,
    view=lambda user, obj=None: obj.get("status") != "archived",
    delete=lambda user, obj=None: False,
)
dashboard.register(Order, fields=["reference", "status"], policy=policy)
```

`view_any` gates the list, `view` is evaluated per record (an IDOR attempt on a
denied record returns `403`, not `404`-by-accident), and `create`, `update`,
`delete`, `restore` and `force_delete` gate the corresponding write paths.

## Impersonation is opt-in

```python
from flaxon.admin import AdminConfig, AdminDashboard

dashboard = AdminDashboard(
    app,
    config=AdminConfig(allow_impersonation=True),
    users=[
        {"username": "admin", "password": "Admin123!", "permissions": ["admin.superuser", "admin.impersonate"]},
        {"username": "viewer", "password": "Viewer123!", "permissions": ["admin.view_dashboard", "order.view_order"]},
    ],
)
```

Rules enforced server-side:

* Disabled unless `allow_impersonation=True`.
* The actor needs `admin.impersonate`.
* Superusers can never be impersonated.
* You cannot impersonate yourself.
* State is bound to the session token; logout ends it.
* Start and stop are both written to the audit log.

While active, every page shows a banner with a one-click **Exit impersonation**
button.
