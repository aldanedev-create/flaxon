# ORM + Admin/CMS: setup, every URL, and custom pages (Jinax and Teloce)

A single end-to-end guide: how the ORM works, how Admin and CMS are wired to it,
which URL every Admin screen lives at, who is allowed to open it, and how to add
your own Admin pages rendered either with Jinax templates or with Teloce
components.

Every route, slug and permission key in this document was read out of a running
`examples/school_portal_orm` application, not inferred from the docs.

Written against **flaxon 0.3.2** (`a7fff8d`) and **teloce-py 0.3.0**.

---

## Contents

1. [The three layers](#1-the-three-layers)
2. [settings.py](#2-settingspy)
3. [The ORM, complete](#3-the-orm-complete)
4. [Wiring Admin and CMS](#4-wiring-admin-and-cms)
5. [Registering ORM models](#5-registering-orm-models)
6. [Every Admin URL, and who may open it](#6-every-admin-url-and-who-may-open-it)
7. [Custom Admin pages with Jinax](#7-custom-admin-pages-with-jinax)
8. [Custom Admin pages with Teloce](#8-custom-admin-pages-with-teloce)
9. [Dashboard widgets and mounted modules](#9-dashboard-widgets-and-mounted-modules)
10. [Gotchas](#10-gotchas)
11. [Source reference](#11-source-reference)

---

## 1. The three layers

| Layer | Import | Owns |
| --- | --- | --- |
| **ORM** | `flaxon.db` (Tortoise 1.x) | Your tables, fields, queries, transactions, migrations |
| **Admin** | `flaxon.admin` | Staff login/roles/permissions, CRUD screens, media, settings, audit, operations |
| **CMS** | `flaxon.admin.cms` | Content types, entries, revisions, taxonomy, comments, menus, scheduling, import/export |

The seam is `model_adapter()`: when you register a Tortoise model, Admin reads
`model._meta.fields_map` and generates a CRUD class for it. That is why ORM
models need no boilerplate — form fields, search, filters, SQL pagination,
transactions, optimistic locking and cascade checks are all derived.

One thing to internalise early: **CMS content does not live in your ORM tables.**
Entries, staff accounts, sessions, media metadata and the audit log live in the
Admin store (its own SQLite file by default, or the same database when you set
`ADMIN_STORE_BACKEND = "orm"`). Public pages read CMS content through the API;
your business rows stay in your own tables.

---

## 2. settings.py

```python
from pathlib import Path
from flaxon.config import env

BASE_DIR = Path(__file__).resolve().parent
env.load(BASE_DIR / ".env")

PROJECT_NAME = "school_portal"
DEBUG = env.bool("FLAXON_DEBUG", default=True)
SECRET_KEY = env.str("FLAXON_SECRET_KEY")

DATABASE_URL = env.str("DATABASE_URL", default=f"sqlite://{BASE_DIR / 'data/app.sqlite3'}")
ALLOWED_HOSTS = env.list("FLAXON_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("FLAXON_CSRF_TRUSTED_ORIGINS", default=[])
TIME_ZONE = "UTC"

ADMIN_ENABLED = True            # staff Admin
CMS_ENABLED = True              # editorial CMS at /admin/cms/
ADMIN_SERVICES_ENABLED = False  # optional microservices control plane
ADMIN_STORAGE_PATH = BASE_DIR / "data/admin.sqlite3"
# ADMIN_STORE_BACKEND = "orm"   # put Admin/CMS metadata in DATABASE_URL instead
```

| Setting | Effect |
| --- | --- |
| `DATABASE_URL` | Tortoise DSN. SQLite for dev; `postgres://…` with `flaxon[postgres]` in prod. Use absolute paths. |
| `ADMIN_ENABLED` | `configure_admin()` returns `None` when false — no Admin routes at all. |
| `CMS_ENABLED` | Creates `app.cms` with a default `page` content type. |
| `ADMIN_STORE_BACKEND = "orm"` | Staff/CMS metadata moves into `DATABASE_URL` (tables `flaxon_admin_entries`, `flaxon_admin_operation_records`; migrations land in `admin_migrations/`). **Set this before `makemigrations`.** It does not move existing data — use `python management.py migrate-admin-store <path/to/admin.sqlite3>`. |
| `ADMIN_STORAGE_PATH` | Where the default SQLite Admin store lives. |
| `ADMIN_SERVICES_ENABLED` | Adds `/admin/services` and `/admin/health`. |

There is no module list in settings. Modules are mounted explicitly in `app.py`,
and the same mounts are used by the web server and by management commands.

---

## 3. The ORM, complete

### 3.1 Models

```python
# models.py
from flaxon.db import Model, fields


class Student(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=120)
    grade = fields.IntField(null=True)
    email = fields.CharField(max_length=200, null=True)
    enrolled_on = fields.DateField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Course(Model):
    id = fields.IntField(primary_key=True)
    code = fields.CharField(max_length=16, unique=True)
    title = fields.CharField(max_length=160)
    seats = fields.IntField(default=30)
    teacher = fields.ForeignKeyField("models.Staff", related_name="courses", null=True)
    students = fields.ManyToManyField("models.Student", related_name="courses")

    def __str__(self):
        return f"{self.code} · {self.title}"


class Staff(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=120)
    role = fields.CharField(max_length=80, null=True)

    def __str__(self):
        return self.name
```

Commonly used fields (Tortoise, re-exported by `flaxon.db`):

| Field | Notes |
| --- | --- |
| `IntField(primary_key=True)` | Explicit primary key; also `BigIntField` |
| `CharField(max_length=…)` | `unique=`, `null=`, `default=`, `index=` |
| `TextField` | Long text; Admin renders a `textarea` |
| `BooleanField(default=False)` | Admin renders a checkbox |
| `IntField` / `FloatField` / `DecimalField(max_digits, decimal_places)` | Numeric |
| `DateField` / `DatetimeField(auto_now=, auto_now_add=)` | `auto_now*` become read-only in Admin |
| `JSONField` | Structured payloads |
| `ForeignKeyField("models.X", related_name=…)` | The **app label is the module name**; root models use `models` |
| `ManyToManyField("models.X", related_name=…)` | Admin renders a multi-select |

### 3.2 Queries

```python
# create / read / update / delete
student = await Student.create(name="Ada Lovelace", grade=10)
one     = await Student.get(id=student.id)
await Student.filter(grade=10).update(grade=11)
await student.delete()

# filtering, ordering, slicing
await Student.filter(name__icontains="ada").order_by("-created_at").limit(20)
await Student.filter(grade__gte=9, name__startswith="A")
await Student.all().count()
await Student.filter(grade__in=[9, 10, 11]).exists()
```

Field lookups use Tortoise's double-underscore syntax (`icontains`, `gte`, `in`,
`isnull`, `startswith`, …). Combine conditions with `Q` objects:

```python
from tortoise.expressions import Q

await Student.filter(Q(grade__gte=10) | Q(name__icontains="ada"))
```

Follow relations without N+1:

```python
courses = await Course.all().prefetch_related("students", "teacher")
for course in courses:
    for student in await course.students.all():
        ...
```

Aggregation:

```python
from tortoise.functions import Count, Avg

await Course.annotate(taken=Count("students")).filter(taken__gt=0)
await Student.annotate(avg_grade=Avg("grade")).values("id", "avg_grade")
```

### 3.3 Transactions and the ORM context

Queries inside HTTP/WebSocket requests run in Flaxon's application-local ORM
context — no setup needed. Outside a request (scripts, background tasks, tests),
bind it yourself:

```python
async with app.db:                     # standalone async work
    await Student.create(name="Grace")

async with in_transaction():           # explicit transaction around writes
    course = await Course.create(code="MATH1", title="Algebra")
    await course.students.add(student)
```

`flaxon.db` exports `Model`, `fields`, `in_transaction`, `atomic`, `Database`.
Do **not** reach for a process-global Tortoise fallback to share connections
between applications, and do not pass `app.db` where an old SQL adapter
(`execute`/`fetch_all`) is expected — `app.db` is the ORM lifecycle object.

### 3.4 Module-owned models

```python
# modules/academics.py
from flaxon.modules import FlaxonModule

academics = FlaxonModule(
    "academics",
    models_module="modules.academics.models",
    admin_module="modules.academics.admin",      # defaults to a sibling admin.py
    migrations_module="modules.academics.migrations",
)
```

Module names are ORM app labels and must be unique; relations reference them
(`fields.ForeignKeyField("academics.Course")`). Mounts happen in `app.py`.

### 3.5 Migrations and management commands

```bash
python management.py check                 # settings + models + Admin registrations
python management.py makemigrations        # generate Python migrations
python management.py migrate --plan        # preview
python management.py migrate               # apply
python management.py migrate --status      # applied history
python management.py sqlmigrate models 0001_initial
python management.py setup-admin           # interactive staff account (hidden password)
python management.py runserver             # dev server (--host/--port/--no-reload)
python management.py shell                 # ORM shell (needs tortoise-orm[ipython])
```

Commit generated migration files; review them before deploying. Startup opens
connections, never migrates.

---

## 4. Wiring Admin and CMS

```python
# app.py (skeleton)
from flaxon import Flaxon
from flaxon.admin.cms import CMSField, ContentType
from flaxon.db.admin import configure_admin
from flaxon.jinax import Jinax
from flaxon.jinax.loaders import CompositeLoader, FileSystemLoader


def create_app():
    app = Flaxon.from_settings()
    settings = app.settings

    # Management mode only needs settings/models/migrations: skip templates,
    # Admin and CMS so commands never open the AdminStore.
    if app.is_management:
        return app

    app.use_templates(Jinax(str(settings.root / "templates"), auto_reload=settings.DEBUG))

    admin = configure_admin(app)           # Registry + admin.py registrars + CMS
    admin.jinax.environment.loader = CompositeLoader(   # let Admin pages use project templates
        [FileSystemLoader(str(settings.root / "templates")), admin.jinax.environment.loader]
    )

    cms = app.cms                          # present when CMS_ENABLED
    cms.register(ContentType(name="news", label="News item", label_plural="News",
                             fields=[CMSField("title", required=True),
                                     CMSField("body", type="richtext"),
                                     CMSField("status", type="select",
                                              choices=["draft", "published"])],
                             list_display=["title", "status", "updated_at"],
                             list_filter=["status"], search_fields=["title", "body"]))

    # Modules that declare requires("cms") must be mounted after cms exists.
    app.container.register_instance("cms", cms)
    app.mount_module(website, prefix="")

    return app


app = create_app()
```

`configure_admin()` (`src/flaxon/db/admin.py`) does five things:

1. Builds a project-local `Registry()`.
2. Imports root `admin.py` plus every mounted module's `admin_module` and calls
   `register(registry)` on each.
3. Creates the `AdminDashboard` with `strict_permissions=True` and
   `session_bound_csrf=True`, `upload_dir=<root>/data/uploads`.
4. Creates the `CMS` (when `CMS_ENABLED`) with a default `page` content type and
   exposes it as `app.cms`.
5. Leaves `dashboard.database = None` — Admin metadata uses the Admin store, not
   the ORM lifecycle object.

Bootsrapping a project:

```bash
python management.py migrate
python management.py setup-admin
python management.py runserver     # /admin/login
```

---

## 5. Registering ORM models

```python
# admin.py (root and/or per module)
from models import Course, Staff, Student


def register(admin):
    admin.register(
        Student,
        list_display=["name", "grade", "email"],
        search_fields=["name", "email"],
        list_filter=["grade"],
        ordering=["name"],
        queryset=lambda user, q: q.filter(grade__gte=9),   # row-level scoping
    )
    admin.register(
        Course,
        list_display=["code", "title", "seats"],
        search_fields=["code", "title"],
        inlines={"students": {"model": Student, "fk": "course_id"}},
    )
    admin.register(Staff, search_fields=["name"], icon="fa-chalkboard-user")
```

| Option | Meaning |
| --- | --- |
| `list_display` | Columns; entries may be callables (`lambda obj: …`) |
| `list_filter` | Exact-match filters rendered as a sidebar |
| `search_fields` | `icontains` OR-combination across the listed columns |
| `ordering` | Default sort |
| `fields` / `readonly_fields` | Form field order and forced read-only fields |
| `fieldsets` | Named headings, e.g. `{"Details": ["name", "description"]}` |
| `widgets` | `{"body": "admin/widgets/body.html"}` — trusted template names only |
| `inlines` | Edit registered children inside the parent form (`fk` is the child's FK **column**) |
| `queryset` | `fn(user, query) -> QuerySet` — tenant/ownership scoping, used for lists, lookups, relationship choices, search and export |
| `can_view` / `can_add` / `can_change` / `can_delete` | Extra business rules; signature `(user)` or `(user, obj)` |
| `actions` | Bulk actions, exposed at `POST /admin/<slug>/actions/<name>` |
| `name` | Overrides the URL slug (default `Model.__name__.lower()`) |
| `icon` | Font Awesome class for the sidebar |
| `validate_import` | Runs during import preview |

What the generated adapter gives you for free:

- Primary keys and `auto_now*` fields become read-only.
- Field types map to `text / number / checkbox / textarea / date / datetime-local`.
- FKs become a permission-filtered dropdown (≤100 rows) or a searchable paginated
  selector; M2M becomes a multi-select.
- Lists are **paginated in SQL**; writes run inside `in_transaction()`.
- Every edit form carries a `_version` fingerprint (field values + relation keys,
  sha256). Missing or stale → 400/409; concurrent saves cannot silently win.
- Deletion previews dependent counts and recursively checks delete permissions on
  registered children; protected relations produce a readable conflict.
- Imports are atomic by default (`?allow_partial=true` for per-row transactions).

**Only registered models are exposed.** Related models you want to pick from must
be registered too.

---

## 6. Every Admin URL, and who may open it

Prefix is `/admin` (`AdminDashboard.url_prefix`); CMS is `/admin/cms`.

### Identity and session

| Path | Purpose |
| --- | --- |
| `/admin/login`, `/admin/logout` | Sign in/out (GET form + POST) |
| `/admin/password-reset`, `/admin/verify-email` | Recovery flows (need a mail sender) |
| `/admin/profile` | Own profile, password, MFA |
| `/admin/profile/webauthn/register/begin` · `/finish` · `/authenticate/begin` · `/authenticate/finish` | Passkeys |
| `/admin/profile/mfa/recovery-codes` | MFA recovery codes |
| `/admin/profile/trusted-devices` (+ `DELETE /<device_id>`) | Trusted devices |

### ORM model pages — `<slug>` is `name=` or `Model.__name__.lower()`

Verified in `examples/school_portal_orm`:

```
student -> /admin/student   student.view_student / add_student / change_student / delete_student
course  -> /admin/course    course.view_course  / add_course  / change_course  / delete_course
staff   -> /admin/staff     staff.view_staff    / add_staff    / change_staff   / delete_staff
```

| Path | Screen | Permission |
| --- | --- | --- |
| `GET /admin/<slug>` | List: search, filters, sort, SQL pagination, bulk actions | `<slug>.view_<slug>` |
| `GET/POST /admin/<slug>/add` | Create form | `<slug>.add_<slug>` |
| `GET /admin/<slug>/<id>` | Detail | `view_` |
| `GET/POST /admin/<slug>/<id>/edit` | Edit (needs `_version`) | `change_` |
| `GET/POST /admin/<slug>/<id>/delete` | Confirm + delete (cascade preview) | `delete_` |
| `GET /admin/<slug>/<id>/history` | Change history | `view_` |
| `GET /admin/<slug>/export` · `POST /admin/<slug>/import` | Export/import | `view_` / `add_` |
| `POST /admin/<slug>/actions/<action>` | Bulk/custom action | auto-registered capability |
| `GET /admin/<slug>/relationships/<field>` | Async options for FK/M2M pickers | `view_` |

### Built-in screens

| Path | Permission |
| --- | --- |
| `/admin/` · `/admin` | Dashboard — `admin.view_dashboard` |
| `/admin/search` | Global search — `admin.view_dashboard` |
| `/admin/users` · `/admin/roles` | `admin.manage_users` · `admin.manage_groups` |
| `/admin/settings` | `admin.manage_settings` |
| `/admin/activity` · `/admin/activity/export` · `/admin/audit/verify` | `admin.view_dashboard` |
| `/admin/operations` · `/admin/operations/tasks` | `admin.view_dashboard` |
| `/admin/notifications` · `/admin/notifications/preferences` | `admin.view_dashboard` |
| `/admin/media` (+ `/folders`, `/bulk`, `/resumable`, `/<file>/signed-url`) | `media.manage_library` |
| `/admin/services` · `/admin/health` | only when `ADMIN_SERVICES_ENABLED` |

### CMS

The CMS UI is a single page at **`/admin/cms/`** (requires `admin.view_dashboard`);
everything else is its JSON API:

```
GET  /admin/cms/api/config
GET  /admin/cms/api/stats
GET  /admin/cms/api/<type>/items                POST /admin/cms/api/<type>/items
GET  /admin/cms/api/<type>/items/<id>           PUT|DELETE /admin/cms/api/<type>/items/<id>
GET  /admin/cms/api/<type>/items/<id>/history   POST /admin/cms/api/<type>/items/<id>/restore/<revision>
POST /admin/cms/api/<type>/actions/<action>
GET  /admin/cms/api/export/<type>               POST /admin/cms/api/import/<type>
GET  /admin/cms/api/scheduler/jobs              POST /admin/cms/api/scheduler/jobs/<job_id>/retry
GET  /admin/cms/api/workspace/<section>         GET  /admin/cms/api/media
GET|POST /admin/cms/api/taxonomies              POST|PATCH|DELETE /admin/cms/api/taxonomies/<name>
GET|POST /admin/cms/api/comments                PATCH|DELETE /admin/cms/api/comments/<id>
GET|PUT  /admin/cms/api/menus/<name>
```

Editorial capabilities: `cms.publish_content`, `cms.moderate_comments`,
`cms.manage_taxonomies`, `cms.manage_menus`, `cms.import_content`,
`cms.export_content`, `cms.restore_revision`.

### How access is decided

Responses, in order — measured on the example app:

| Situation | Result |
| --- | --- |
| Not signed in | **401** (every `/admin/*` path, including custom pages) |
| Signed in, lacks the capability | **403** |
| Model not registered | **404** (`NotFound: Unknown admin model`) |
| Mutating request without CSRF | **403** |

Granting access:

- **Roles UI** — `/admin/roles` ships Administrator, Content Editor, Publisher,
  Media Manager, Warehouse Staff, Support Agent, Read Only with descriptions and
  checkboxes. Nobody has to type permission keys.
- **Custom capability** — `admin.register_permission("reports.view_reports",
  "View reports", "Reporting")` then guard your page with it.
- **Row/object rules** — `queryset=` and `can_*` hooks (section 5).
- `admin.superuser` bypasses capability checks; assign sparingly.

---

## 7. Custom Admin pages with Jinax

```python
async def school_overview(request):
    """Custom Admin page reading straight from the ORM and CMS."""
    return await admin.jinax.render_response(
        "admin_school_overview.html",
        {
            "title": "School overview",
            "student_count": await Student.all().count(),
            "course_count": await Course.all().count(),
            "staff_count": await Staff.all().count(),
            "news_count": len([i for i in cms.content_types["news"].items.values()
                               if i.get("status") == "published"]),
        },
    )


admin.add_view(
    school_overview,
    "School overview",
    url="school-overview",       # -> /admin/school-overview
    category="School",           # metadata (see gotchas)
    icon="fa-school",            # Font Awesome class
    permission="admin.view_dashboard",
)
```

`add_view(view, name, *, url=None, category="Custom", icon="fa-puzzle-piece",
methods=None, permission="admin.view_dashboard")`:

- Route: `/admin/<url or name.lower().replace(" ", "-")>`, route name
  **`admin_custom_<url>`** — reverse it with
  `app.router.url_for("admin_custom_school-overview")`.
- The callback receives **only `request`** (no dependency injection). Sync or
  async; return `HTMLResponse`, `JSONResponse`, or a rendered template.
- `permission` is checked before your code runs; object-level checks are still
  yours to make.
- `methods` defaults to `{"GET"}`. **POST/PUT/PATCH/DELETE must send the
  dashboard CSRF token in an `X-CSRF-Token` header** (`session_bound_csrf=True`).
- The page appears in the sidebar and the mobile menu automatically.

`templates/admin_school_overview.html` — extend the Admin shell so the page keeps
the navigation and styling:

```jinja
{% extends "admin/base.html" %}

{% block title %}School overview{% endblock %}

{% block content %}
<div class="corporate-page">
  <header class="corporate-header">
    <div>
      <p class="admin-eyebrow">Northstar Academy</p>
      <h1>School overview</h1>
      <p class="corporate-subtitle">Live numbers from the ORM and the CMS.</p>
    </div>
  </header>

  <div class="grid cards">
    <div class="card"><div class="muted">Students</div><div class="metric">{{ student_count }}</div></div>
    <div class="card"><div class="muted">Courses</div><div class="metric">{{ course_count }}</div></div>
    <div class="card"><div class="muted">Staff</div><div class="metric">{{ staff_count }}</div></div>
    <div class="card"><div class="muted">Published news</div><div class="metric">{{ news_count }}</div></div>
  </div>

  <p class="muted">
    {# `dashboard` is a Jinax global in Admin templates. #}
    <a href="{{ dashboard.url_prefix }}/student">Open the student list</a> ·
    <a href="{{ dashboard.url_prefix }}/cms/">Open the CMS</a>
  </p>
</div>
{% endblock %}
```

`admin/base.html` exposes `title`, `extra_head`, `content` and `extra_scripts`
blocks, and adds `dashboard` as a Jinax global (`dashboard.can_access_model(user,
"student", "change")`, `dashboard.url_prefix`, …).

---

## 8. Custom Admin pages with Teloce

Enable Teloce **before** the management guard so build/typecheck commands still
work:

```python
app.use_teloce(
    project_root=settings.root,
    ui_dir="ui",                       # source tree: ui/app.html, ui/pages/*.html
    title="Northstar Academy",
    favicon="/school-static/favicon.svg",
)
```

The compiler writes to `.flaxon/build/` and serves it at `/_flaxon`
(`static_url`). Files map predictably:

```
ui/app.html            -> /_flaxon/ui/app.js        (+ .js.map in debug)
ui/pages/Home.html     -> /_flaxon/ui/pages/Home.js
ui/pages/Students.html -> /_flaxon/ui/pages/Students.js
pages are routed automatically: Home.html -> "/", Students.html -> "/students"
```

### 8.1 Full-page Teloce screen (no Admin chrome)

```python
async def live_overview(request):
    return await request.compile(
        "pages/AdminOverview.html",          # relative to ui_dir
        {"title": "Live overview", "api": "/api/admin/overview"},
        title="Live overview",
    )

admin.add_view(live_overview, "Live overview", url="live-overview", icon="fa-bolt")
```

`request.compile()` delegates to `app.teloce.render()`, which emits a complete
document that mounts the component into `#app`. Use this for dashboards,
full-screen tools and anything that does not need the Admin sidebar.

### 8.2 Teloce component inside the Admin shell (recommended)

Keep Admin navigation, drop a reactive component into the content area:

```python
async def live_panel(request):
    return await admin.jinax.render_response(
        "admin_live_panel.html",
        {"title": "Live panel"},
    )

admin.add_view(live_panel, "Live panel", url="live-panel", icon="fa-chart-line")
```

```jinja
{# templates/admin_live_panel.html #}
{% extends "admin/base.html" %}
{% block title %}Live panel{% endblock %}

{% block content %}
<div class="corporate-page">
  <h1>Live panel</h1>
  <div id="admin-live"></div>
</div>
{% endblock %}

{% block extra_scripts %}
{# Production builds emit /_flaxon/styles.css; dev builds keep CSS per component. #}
<script type="module">
  import { mount } from "/_flaxon/ui/pages/AdminLive.js";
  mount("#admin-live", { api: "/api/admin/overview" });
</script>
{% endblock %}
```

`ui/pages/AdminLive.html`:

```html
<template>
  <section class="grid cards">
    <div class="card"><div class="muted">Students</div><div class="metric">{{ stats.students }}</div></div>
    <div class="card"><div class="muted">Courses</div><div class="metric">{{ stats.courses }}</div></div>
    <div class="card"><div class="muted">Staff</div><div class="metric">{{ stats.staff }}</div></div>
  </section>
</template>

<script>
export default {
  props: ["api"],
  data() {
    return { stats: {} };
  },
  async mounted() {
    this.stats = await fetch(this.api).then(r => r.json());
  },
};
</script>
```

### 8.3 Feeding the component: a guarded JSON endpoint

Anything outside `/admin/*` is **not** protected by Admin, so authorize
explicitly:

```python
# modules/adminapi.py
from flaxon.http import JSONResponse
from flaxon.modules import FlaxonModule

from models import Course, Staff, Student

adminapi = FlaxonModule("adminapi")


@adminapi.get("/overview")
async def overview(request):
    dashboard = request.app._flaxon_admin_dashboard
    user = await dashboard.auth.current_user(request)          # 401 when anonymous
    await dashboard.auth.authorize_async(user, "admin.view_dashboard")   # 403 without it
    return JSONResponse({
        "students": await Student.all().count(),
        "courses": await Course.all().count(),
        "staff": await Staff.all().count(),
    })
```

Mount it (`app.mount_module(adminapi, prefix="/api/admin")`) and point the
component at `/api/admin/overview`. Browser requests carry the Admin session
cookie, so `current_user()` resolves the same staff identity.

### 8.4 Development niceties

With `DEBUG=True`, Flaxon injects a Teloce error overlay: source-mapped stack
frames back to `ui/pages/*.html`, a hint for "X is not defined", and an
**Open in editor** link (`vscode://file/...`). Configure it with
`app.use_teloce(editor="vscode", editor_remote="vscode-remote://ssh-remote+host",
editor_path_map={"/app": "/home/me/project"})`.

---

## 9. Dashboard widgets and mounted modules

```python
# Widgets run once per dashboard request; sync, async, or objects with render().
async def headline(user, dashboard):
    return {"title": "Students", "value": await Student.all().count()}

admin.register_widget(headline)
```

```python
# Mount a whole module under Admin, keeping its own routes/templates/assets.
admin.mount_module(
    reports,
    navigation=[{"name": "Monthly report", "path": "monthly", "icon": "fa-chart-line"}],
)
# -> /admin/extensions/reports/monthly, plus a navigation entry
```

---

## 10. Gotchas

| # | Trap | Reality |
| --- | --- | --- |
| 1 | Plain (non-Tortoise) class models silently fail to save | Only Tortoise models get generated CRUD. Plain classes need `get_instances / get_instance / create_instance / update_instance / delete_instance`. Admin now renders a 400 with a form error and flags the edit page instead of pretending the write worked. |
| 2 | POSTing edit forms from scripts | You must round-trip the hidden `_version`; missing/stale → 400/409. |
| 3 | Registering relations | Use the FK **column** name (`author_id`, not `author`), or the field is silently dropped from the writable set. |
| 4 | `app.db` as a `database=` argument | `app.db` is the ORM lifecycle object, not the legacy SQL adapter. Leave `dashboard.database = None` with `configure_admin()`. |
| 5 | Custom page URLs vs model slugs | Static routes win (`Router.match` checks the static table first), so `/admin/live-panel` is safe even if a model were named `live_panel`. |
| 6 | Navigation visibility | Sidebar entries for custom pages are rendered for **everyone** who can see the dashboard; the link 403s for users without `permission`. Narrow it with `register_permission` if that matters. |
| 7 | `category=` on `add_view` | Stored, but `admin/base.html` renders a flat list — it does not group. |
| 8 | Expecting dependencies in a custom page callback | `add_view` calls `view(request)` only — there is no injection of `cms`, `db` or container services. Capture what you need from the enclosing app factory (or from `request.app`). |
| 9 | Admin templates without `CompositeLoader` | `admin.jinax` only knows the package templates. Add the project directory before `render_response("my_page.html")` works. |
| 10 | `ADMIN_STORE_BACKEND = "orm"` after the fact | It changes where metadata is written; it does not copy anything. Use `migrate-admin-store`. |
| 11 | CMS "not showing up" | `CMS_ENABLED=True` **and** mount modules that `require("cms")` only after `configure_admin(app)`. |
| 12 | Teloce component not mounting inside Admin | The entry path must match the build output (`/_flaxon/ui/pages/<Name>.js`); check `.flaxon/build/` and the browser network tab. |

---

## 11. Source reference

| Concern | File |
| --- | --- |
| ORM exports, `Database` lifecycle | `src/flaxon/db/__init__.py`, `src/flaxon/db/integration.py` |
| `configure_admin`, `model_adapter` | `src/flaxon/db/admin.py` |
| Dashboard, all Admin routes, `add_view`, `mount_module` | `src/flaxon/admin/dashboard.py` |
| Registry, `AdminModel` options, permission hooks | `src/flaxon/admin/registry.py` |
| Permission catalog, canonical keys, providers | `src/flaxon/admin/authorization.py` |
| Auth (login, MFA, sessions, `current_user`) | `src/flaxon/admin/services.py` |
| List/detail/create/update/delete views | `src/flaxon/admin/views.py` |
| CMS types, entries, API routes | `src/flaxon/admin/cms.py` |
| Admin shell template (blocks) | `src/flaxon/admin/templates/admin/base.html` |
| Teloce integration, `render`, build/serve | `src/flaxon/teloce.py` |
| Request helpers (`render`, `compile`) | `src/flaxon/http/request.py` |

Runnable references: `examples/school_portal_orm` (Jinax + ORM + CMS + custom
page) and `examples/school_portal_teloce` (Teloce SPA + ORM + CMS + custom page).
Related reading: [ORM guide](orm.md), [Admin/CMS guide](admin-cms.md),
[admin API](../api/admin.md), [Teloce API](../api/teloce.md).
