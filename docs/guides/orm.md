# Models, settings, and management commands

Flaxon 0.2.7 integrates Tortoise ORM 1.1.7. `flaxon.db` exports its models, fields,
and transaction helpers. Existing `flaxon.database` adapters and JSON migration
runners remain available for existing applications; new full-stack starters use
Python migrations.

## Start a project

Install this release from the repository until it is published to PyPI:

```bash
python -m pip install -e ".[standard,admin]"
flaxon new project_manager
cd project_manager
python -m pip install -e .
python management.py check
python management.py makemigrations
python management.py migrate --plan
python management.py migrate
python management.py setup-admin
python management.py runserver
```

The CLI creates `.venv`; activate it before installing your generated project.
`flaxon run app:app --reload` continues to work. `runserver` is a development
command; use an ASGI server without reload for production.

## File responsibilities

| File | Responsibility |
| --- | --- |
| `settings.py` | Paths, database URL, security, enabled Admin/CMS features |
| `app.py` | Create the application and explicitly mount modules |
| `models.py` | Root project models |
| `admin.py` | `register(admin)` explicitly registers editable models |
| `management.py` | Small entry point to Flaxon's management command system |
| `migrations/` | Generated, version-controlled Python migration files |

There is no module mount list in settings. The same mounts in `app.py` are used
by the web server and management commands. The starter's management mode skips
Jinax/Teloce setup and AdminStore construction; model discovery doesn't compile
JavaScript or connect to the database.

## Settings

```python
from pathlib import Path
from flaxon.config import env

BASE_DIR = Path(__file__).resolve().parent
env.load(BASE_DIR / ".env")
PROJECT_NAME = "project_manager"
DEBUG = env.bool("FLAXON_DEBUG", default=True)
SECRET_KEY = env.str("FLAXON_SECRET_KEY")
DATABASE_URL = env.str("DATABASE_URL", default=f"sqlite://{BASE_DIR / 'data/app.sqlite3'}")
ALLOWED_HOSTS = env.list("FLAXON_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("FLAXON_CSRF_TRUSTED_ORIGINS", default=[])
TIME_ZONE = "UTC"
ADMIN_ENABLED = True
CMS_ENABLED = True
ADMIN_SERVICES_ENABLED = False
ADMIN_STORAGE_PATH = BASE_DIR / "data/admin.sqlite3"
```

Environment variables take precedence over `.env`. Booleans accept true/false,
yes/no, on/off, and 1/0; other values fail clearly. Lists are comma-separated.
Use absolute SQLite paths so commands run from any directory select the same DB.
Production (`DEBUG=False`) requires a persistent secret of at least 32 characters
and explicit hosts. Trusted CSRF origins include the scheme and host, without a
path. UTC and timezone-aware ORM timestamps are the default.

For PostgreSQL, install `flaxon[postgres]` and set a Tortoise-compatible URL:
`postgres://USER:URL_ENCODED_PASSWORD@HOST:5432/DATABASE`. The starter's staff and
CMS metadata use SQLite by default. To put them in the same ORM database, set
`ADMIN_STORE_BACKEND = "orm"` before generating and applying migrations.
The existing PostgreSQLAdminStore remains available for manually configured apps.
Changing the domain ORM URL does not automatically migrate Admin metadata.

## Models and queries

```python
from flaxon.db import Model, fields

class Project(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=120, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return self.name
```

```python
project = await Project.create(name="Launch the website")
projects = await Project.filter(name__icontains="website").order_by("-created_at")
project.name = "Launch the portfolio"
await project.save()
```

Queries run in Flaxon's application-local ORM context during HTTP/WebSocket
requests. For standalone async work, use `async with app.db:`. Do not use a
process-global Tortoise fallback to share connections across applications.

## Module-owned models

```python
from flaxon.modules import FlaxonModule

projects = FlaxonModule(
    "projects",
    models_module="modules.projects.models",
    admin_module="modules.projects.admin",
    migrations_module="modules.projects.migrations",
)
```

Mount explicitly in `app.py` after `Flaxon.from_settings()`:

```python
app.mount_module(projects, prefix="/api/projects")
```

The migrations path defaults to the model package's `migrations` package.
`admin_module` defaults to a sibling `admin.py` if present. Module names are ORM
app labels and must be unique. Root models use the `models` label. Relations use
these labels, e.g. `fields.ForeignKeyField("models.Project")`.

## Admin registration

```python
from models import Project

def register(admin):
    admin.register(Project, search_fields=["name"], ordering=["-created_at"])
```

Call `configure_admin(app)` after mounting modules in the non-management branch
of your factory. It creates a project-local registry, strict permissions, durable
staff accounts, optional CMS, and session-bound CSRF. Only registered models are
exposed. Primary keys and automatic timestamps are read-only. Forms derive basic
types, required flags and length limits from ORM fields. Foreign keys use a
permission-filtered choice list up to 100 related records, otherwise a searchable
paginated selector. Many-to-many fields receive multiple-selection controls.
Related models must be explicitly registered; both displayed choices and submitted
IDs obey their model/object permissions. Model validation remains authoritative.

## Management commands

- `check`: validate settings, discover models, and validate Admin registrations.
- `makemigrations [LABEL] --name DESCRIPTION`: generate Python migrations.
- `makemigrations LABEL --empty`: scaffold a data/custom migration.
- `migrate [LABEL [MIGRATION]]`: apply migrations or target a prior migration.
- `migrate --status`: show applied migration history.
- `migrate --plan`: show pending operations without applying them.
- `sqlmigrate LABEL MIGRATION`: inspect the generated SQL.
- `setup-admin` / `createsuperuser`: prompt for a staff account and hidden password.
- `shell`: Tortoise's ORM-aware shell; install `tortoise-orm[ipython]` first.
- `runserver`: development server; accepts `--host`, `--port`, `--no-reload`.
- Module commands remain available through `flaxon_cli.py`, e.g. `welcome`.

Commit migration files. Review generated operations before deployment. Server
startup opens connections, not tables; it never runs migrations automatically.
Application-auth accounts and staff Admin accounts are separate concerns.

## Existing JSON migrations

Do not delete JSON history or run a new initial migration against populated
legacy tables. Back up the database, keep the legacy runner operational, and
compare model-generated schema with the existing schema in a disposable clone.
A matching existing schema can be baselined with Tortoise's `migrate --fake`
after review; use the Tortoise CLI with an explicitly exported ORM configuration
for that advanced operation. The default Flaxon wrapper does not offer fake
migration flags. Test subsequent migration/rollback and restore before switching
production. There is no automatic data conversion or assumption that the old
`migrations` tracking table means the new ORM migration has been applied.

## Admin hardening and compatibility

The starter uses `strict_permissions=True` and `session_bound_csrf=True`.
Existing manual AdminDashboard setups retain legacy defaults for compatibility;
opt into those settings and use a shared persistent SECRET_KEY across workers.
Always fetch a fresh CSRF token after sign-in; pre-login tokens are not valid for
the authenticated session. Configured browser Origins are enforced on mutations.
CSRF protection does not authorize a user: model and object rules are enforced
separately on search, export, edit, delete, and bulk actions.

CMS editing requires authentication by default. Explicit `allow_unauthenticated`
is only for deliberately public/demonstration setups. A standalone authenticated
CMS without AdminDashboard must supply its own CSRF protector. Publication rights
are checked for edits to live content, imports, scheduling, and restoration.

ORM lists use database pagination. Legacy custom `get_instances()` adapters and
Python object-permission hooks may still scan records in memory; large or
multi-tenant datasets need scoped database adapters. Audit/export/search snapshots
redact credential-like keys. This is targeted hardening, not a complete security
certification or parity claim with Django Admin.


## Simple Admin customization

```python
from models import Project, Task

def register(admin):
    admin.register(
        Project,
        search_fields=["name"],
        fieldsets={"Details": ["name", "description"]},
        queryset=lambda user, query: query.filter(owner_id=user.id),
        inlines={"tasks": {"model": Task, "fk": "project_id"}},
    )
    admin.register(Task, search_fields=["title"])
```

`queryset(user, query)` scopes the base ORM query for lists, lookups, relationship
choices, search and export. Return a QuerySet; an async function may return one.
Use it for tenant/ownership filtering. Optional `can_view`, `can_add`,
`can_change`, and `can_delete` hooks provide additional business rules. Python
object hooks filter before pagination, giving correct counts, but may scan
records; the query hook avoids that cost for large tables.

`fieldsets` inserts named headings before the first configured field. Existing
`fields` still controls order. `widgets={"body": "admin/widgets/body.html"}`
selects a trusted Jinax template for a field; templates receive `field_name`,
`schema`, and `current_value`. Never derive template names from request input.

Inlines edit registered child models within a parent form. `fk` names the child's
foreign-key ID column. Each operation enforces the child's create/change/delete
permission and hook, and existing children must belong to that parent. Parent
and child changes share a transaction. Forms support at most 100 children and
200 many-to-many selections; larger workflows should use the separate model
list. Inline fields currently use scalar inputs; complex child editors can use a
custom Admin view. Custom business side effects must run after a successful
transaction; database rollback cannot undo email or external service calls.

Validation errors preserve submitted scalar values and display field errors.
Unique/relationship conflicts remain explicit 409 responses. ORM edit forms
include a fingerprint of the record; stale or missing versions cannot overwrite
newer changes. Atomic conditional writes protect against concurrent saves,
including models without `updated_at`. The fingerprint includes many-to-many selections. Inline existing-child saves
carry child versions.

Deletion confirmation shows direct dependent counts and database deletion rules.
Cascade deletion additionally checks registered dependent-model and object delete
permissions recursively. Protected relationships produce a readable conflict.

ORM imports are atomic by default. `?allow_partial=true` gives each row its own
transaction and reports the actual successful count; external side effects remain
the application's responsibility. Import preview runs the configured import
validator; database constraints are checked when applying the import.

## ORM-backed Admin/CMS metadata

Opt in through `settings.py`:

```python
ADMIN_STORE_BACKEND = "orm"
```

```bash
python management.py makemigrations
python management.py migrate
python management.py setup-admin
```

Flaxon adds the `flaxon_admin` model label and generated `admin_migrations/`
package. Commit those Python migrations. This stores staff records, sessions,
CMS metadata, audit metadata and operations through the ORM in `DATABASE_URL`.
No Admin table is created silently on server startup. The store preserves the
existing synchronous service contract using a dedicated thread/event loop with
separate ORM connections; calls are synchronous and are not a nonblocking
request API. Media file bytes still need persistent filesystem or object storage.

To move an existing SQLite store, stop all writers, back up both databases,
apply the ORM migrations, and copy into an **empty destination**:

```bash
python management.py migrate-admin-store /absolute/path/to/admin.sqlite3
```

The copy is transactional, preserves operation timestamps, refuses a nonempty
destination, and leaves the source unchanged. Test sign-in, CMS records, sessions
and audit history before switching production traffic. Retain the source backup
for rollback. Changing the setting by itself does not copy existing records.

Admin bundles Alpine.js 3.14.3 with its MIT license so the CMS and core Admin
interactions do not require downloading that runtime from a CDN. Cosmetic fonts,
icons and Tailwind enhancements still reference external assets. Browser
regression tests block those external requests and exercise the local controls.


## Admin/CMS and database adapters

The ORM lifecycle object at `app.db` is not the older SQL adapter interface.
Admin and CMS use their durable AdminStore by default; they only automatically
use a legacy database object implementing both `execute()` and `fetch_all()`.
Choose `ADMIN_STORE_BACKEND = "orm"` explicitly to store metadata through the ORM.
Do not pass the lifecycle object as `database=` to AdminDashboard or CMS.
