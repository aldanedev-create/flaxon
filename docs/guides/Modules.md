# Modules Guide

`flaxon/modules.py` adds a Flask-blueprint-style composition unit to
Flaxon: `FlaxonModule`. It's one file, drops into an existing Flaxon
install with no other changes, and is built entirely on Flaxon's own
real primitives (`Router`, `Container`, `on_startup`/`on_shutdown`,
`mount_static`, Jinax) rather than copying Flask's design wholesale.

Every example on this page has been run and verified, not just written.


Importing it is what activates it -- it attaches `mount_module()` onto
the real `Flaxon` app class the moment it's imported:

```python
from flaxon.modules import FlaxonModule   # this import alone is enough
```

If you're also using `flaxon_cli.py`-at-project-root for custom CLI
commands (see the CLI section below), make sure your `flaxon/cli/discovery.py`
has the `sys.path` fix -- without it, that specific discovery path silently
finds nothing when run through the installed `flaxon` command (a real,
pre-existing bug, unrelated to modules.py). The `./cli/*.py` discovery path
doesn't need the fix and works either way.

---

# Quick Start

```python
from flaxon import Flaxon
from flaxon.modules import FlaxonModule

users = FlaxonModule("users")

@users.get("/")
async def list_users():
    return {"users": ["alice", "bob"]}

@users.get("/<int:user_id>")
async def get_user(user_id: int):
    return {"id": user_id}

app = Flaxon("my-app")
app.mount_module(users, prefix="/api/v1/users")
```

Run with `flaxon run app:app --reload`. `GET /api/v1/users/` and
`GET /api/v1/users/42` both work. The module itself has no idea it's
mounted under `/api/v1/users` -- that's decided entirely at
`mount_module()` time, not baked into the module when it's authored.
That's the core design difference from Flask blueprints, whose
`url_prefix` handling has historically been a source of confusion.

---

# Large application pattern

Use one `FlaxonModule` for each business capability. Keep the application
factory responsible for composition, and keep feature code responsible for
its own routes, schemas, services, templates, and tests. This lets a large
application grow without turning `app.py` into a registry of unrelated
handlers.

```text
myapp/
|-- app/
|   |-- main.py
|   |-- config.py
|   `-- modules/
|       |-- catalog/
|       |   |-- __init__.py
|       |   `-- module.py
|       |-- accounts/
|       |   |-- __init__.py
|       |   `-- module.py
|       `-- ai_tools/
|           |-- __init__.py
|           `-- module.py
|-- tests/
`-- pyproject.toml
```

The entry point should only create the app and mount features:

```python
# app/main.py
from flaxon import Flaxon

from app.modules.accounts.module import install_accounts
from app.modules.catalog.module import install_catalog


def create_app() -> Flaxon:
    app = Flaxon("store", debug=False)
    install_accounts(app)
    install_catalog(app)
    return app


app = create_app()
```

Define routes and request models beside the feature that owns them:

```python
# app/modules/catalog/module.py
from typing import Any

from pydantic import BaseModel

from flaxon.modules import FlaxonModule

catalog = FlaxonModule("catalog")


class CreateProduct(BaseModel):
    name: str
    price: float


@catalog.post("/")
async def create_product(product: CreateProduct) -> CreateProduct:
    # Replace this with a service/repository call in a real application.
    return product


def install_catalog(app: Any) -> None:
    app.mount_module(catalog, prefix="/api/products")
```

The same feature can expose MCP tools without mixing protocol startup into the
HTTP application:

```python
# app/modules/ai_tools/module.py
from typing import Any

from fastmcp import FastMCP

from flaxon.integrations.fastmcp import mount_fastmcp

mcp = FastMCP("Store Tools")


@mcp.tool
async def find_product(name: str) -> dict[str, str | bool]:
    return {"name": name, "available": True}


def install_ai_tools(app: Any, auth_provider: Any) -> None:
    mount_fastmcp(
        app,
        mcp,
        path="/mcp",
        auth=auth_provider,
        require_auth=True,
        stateless_http=True,
    )
```

`auth_provider` is your application's configured authentication provider. Do
not replace it with `require_auth=False` for a public deployment. Do not call
`mcp.run()` from a module; `mount_fastmcp()` owns the mounted ASGI lifecycle.

## Decide where code goes

| Code | Location | Why |
|---|---|---|
| URL and HTTP method | `FlaxonModule` route | Defines the public HTTP contract |
| JSON input shape | Pydantic model or Flaxon `Schema` | Gives clients predictable validation errors |
| Business rules | Service called by the route/tool | Reusable from HTTP, MCP, tasks, and tests |
| Database queries | Repository or adapter | Keeps storage replaceable and testable |
| HTML | Feature-owned Jinax templates | Keeps presentation out of services |
| MCP tools/resources | Feature-owned `FastMCP` instance | Keeps MCP names and permissions together |
| App-wide wiring | `create_app()` | Makes startup, testing, and deployment consistent |

Install the optional integrations only when you use them:

```bash
python -m pip install "flaxon[pydantic,mcp]"
flaxon run app.main:app --reload
```

The complete runnable versions are in
`examples/pydantic_api/` and `examples/fastmcp_app/`.

---

# Why the prefix is decided at mount time (not authoring time)

This matters in practice, not just in theory -- it's what makes a
module reusable for API versioning without copy-pasting it:

```python
api = FlaxonModule("api")

@api.get("/ping")
async def ping():
    return {"pong": True}

app = Flaxon("versioned-app")
app.mount_module(api, prefix="/v1", name="api-v1")
app.mount_module(api, prefix="/v2", name="api-v2")
```

Both `/v1/ping` and `/v2/ping` work, from the exact same module
instance. The `name=` is required here because two mounts of the same
module default to the same name and would otherwise collide -- see
"Duplicate mounts" below.

---

# Declaring dependencies with `requires()`

A module can declare what it needs from the app's dependency-injection
container. If the dependency isn't registered, mounting fails
immediately with a clear error -- not an `AttributeError` three requests
later in production.

```python
from flaxon import Flaxon
from flaxon.modules import FlaxonModule, ModuleDependencyError

posts = FlaxonModule("posts")
posts.requires("db")

@posts.get("/")
async def list_posts(db):
    return await db.fetch_all("SELECT * FROM posts")

app = Flaxon("blog-app")

try:
    app.mount_module(posts, prefix="/posts")
except ModuleDependencyError as exc:
    print(exc)  # "Module 'posts' requires ['db'] in app.container, but ..."

# Register the dependency, then it mounts fine:
app.container.register_instance("db", my_database_connection)
app.mount_module(posts, prefix="/posts")
```

Handlers ask for dependencies by parameter name (`db` above) -- same
injection convention as any other Flaxon route, since modules just wrap
the real router underneath.

---

# Module-scoped request hooks

`before_request` and `after_request` only run for routes registered on
*that* module -- they don't affect routes elsewhere in your app.

```python
from flaxon import Flaxon
from flaxon.modules import FlaxonModule
from flaxon.exceptions import Unauthorized

admin_area = FlaxonModule("admin_area")

@admin_area.before_request
async def require_admin_header(request):
    if request.headers.get("x-admin-key") != "secret":
        raise Unauthorized("Missing or invalid admin key")

@admin_area.after_request
async def log_access(request, result):
    print(f"Admin route accessed: {request.path}")

@admin_area.get("/stats")
async def stats():
    return {"visits": 1000}

app = Flaxon("app-with-admin-area")
app.mount_module(admin_area, prefix="/admin-area")
```

A `before_request` that raises genuinely blocks the handler -- it never
runs at all, not even partially. This is implemented by wrapping each
endpoint at mount time (not by patching Flaxon's internal request
dispatcher, which would be far riskier) -- the wrapper preserves the
original handler's exact signature, so path params, `request` injection,
and DI-resolved dependencies still work correctly whether or not the
handler itself declares a `request` parameter.

---

# Module-scoped error handlers

```python
from flaxon import Flaxon
from flaxon.http import JSONResponse
from flaxon.modules import FlaxonModule

class PostNotFound(Exception):
    pass

posts = FlaxonModule("posts")

@posts.errorhandler(PostNotFound)
async def handle_missing_post(request, exc):
    return JSONResponse({"error": str(exc)}, status_code=404)

@posts.get("/<int:post_id>")
async def get_post(post_id: int):
    if post_id not in real_posts_store:
        raise PostNotFound(f"No post with id {post_id}")
    return real_posts_store[post_id]

app = Flaxon("blog")
app.mount_module(posts, prefix="/posts")
```

Only exceptions of the registered type (or a subclass) raised **within
this module's own routes** are caught here. Exceptions from unrelated
routes elsewhere in the app, or exception types this module hasn't
registered a handler for, propagate as normal and hit your app's
regular error handling.

---

# Static files and templates

```python
from flaxon import Flaxon
from flaxon.modules import FlaxonModule
from flaxon.http import Request

blog = FlaxonModule("blog", template_dir="templates", static_dir="static")

@blog.get("/")
async def home(request: Request):
    return await request.render("index.html")

app = Flaxon("blog-app", debug=True)
app.mount_module(blog, prefix="/blog")
```

- `static_dir` is served at `/static/<module name>/...` (uses the real
  `app.mount_static()`, which is idempotent and path-traversal safe).
- `template_dir` is wired into the app's template loader. If the app
  doesn't have a template engine set up yet, mounting the module sets
  one up for you. If it already does, the module's templates become a
  **fallback** -- the app's own templates always take precedence for a
  same-named file. This mirrors Flask's blueprint template-namespacing
  intent without requiring a `<module_name>/` prefix convention on
  every filename.

---

# Lifecycle hooks

```python
from flaxon import Flaxon
from flaxon.modules import FlaxonModule

blog = FlaxonModule("blog")

@blog.on_startup
async def warm_cache():
    print("Warming blog cache...")

@blog.on_shutdown
async def flush_cache():
    print("Flushing blog cache...")

app = Flaxon("blog-app")
app.mount_module(blog, prefix="/blog")
```

These forward directly into the app's real ASGI lifespan hooks
(`app.on_startup`/`app.on_shutdown`) -- they fire on real startup/shutdown
events (e.g. under `flaxon run`), the same as any hook registered
directly on the app.

---

# Nested modules

```python
from flaxon import Flaxon
from flaxon.modules import FlaxonModule

v1_users = FlaxonModule("users")

@v1_users.get("/")
async def list_users():
    return {"users": []}

api = FlaxonModule("api")
api.register_module(v1_users, prefix="/v1/users")

app = Flaxon("nested-app")
app.mount_module(api, prefix="/api")
# final resolved path: GET /api/v1/users/
```

Nest as deep as you want. A module can't be nested inside itself, and
cycles (`a` nests `b`, `b` nests `a`) are detected and rejected with
`ModuleCycleError` at `register_module()` time, before you ever try to
mount anything.

---

# CLI commands owned by a module

Flaxon's CLI already supports plugin-style command discovery from two
places: a `flaxon_cli.py` at your project root, or any `./cli/*.py`
file. `FlaxonModule` hooks into this directly -- no core CLI changes
needed.

```python
# cli/blog.py
from flaxon.modules import FlaxonModule

blog = FlaxonModule("blog")

@blog.cli_command("seed", help_text="Seed demo blog posts")
async def seed_posts(console):
    console.info("Seeding demo posts...")
    # ... insert demo data ...

blog.install_cli_commands(globals())
```

Then:

```bash
flaxon --help     # "seed" shows up in the command list
flaxon seed       # actually runs it
```

Command functions can be sync or async, and can optionally take `args`
as a second parameter if they need to read CLI flags:

```python
@blog.cli_command("import")
async def import_posts(console, args):
    console.info(f"Importing from: {args.command}")
```

**Use `./cli/*.py`, not `flaxon_cli.py`, unless you've applied the
`discovery.py` fix.** The `flaxon_cli.py`-at-project-root path relies on
plain `import flaxon_cli`, which only works if the current directory
happens to already be on `sys.path` -- verified this is not reliably
true when running the installed `flaxon` console script. `./cli/*.py`
uses explicit file loading instead and works regardless.

---

# Testing a module in isolation

No full app needed:

```python
import asyncio
from flaxon.modules import FlaxonModule, ModuleTestClient

async def test_ping():
    mod = FlaxonModule("api")

    @mod.get("/ping")
    async def ping():
        return {"pong": True}

    client = ModuleTestClient(mod)
    response = await client.request("GET", "/ping")
    assert response.status_code == 200

asyncio.run(test_ping())
```

`ModuleTestClient` builds a throwaway `Flaxon` app, mounts your module
at the root, and wraps it in the real `AsyncTestClient` -- genuinely
low-risk since `AsyncTestClient` only needs a bare ASGI callable, not
anything Flaxon-specific.

---

# Production considerations

## Duplicate mounts fail loudly, on purpose

```python
app.mount_module(users, prefix="/a")
app.mount_module(users, prefix="/b")  # raises ModuleAlreadyMountedError
```

This is intentional -- a second full-module mount under the same
default name is more likely a real bug (accidentally mounting the same
module twice) than something you meant to do. If you *do* mean it
(e.g. API versioning), pass distinct `name=` values, as shown earlier.

## `requires()` as a deploy-time safety net

Put every hard dependency your module needs in `requires()`. Combined
with mounting all your modules at app-startup (not lazily, not inside a
request handler), a misconfigured deployment -- a missing database
connection, a missing cache client -- fails immediately when the app
starts, not on the first real request from a user.

## Error handlers and information leakage

A module-scoped `errorhandler` fully controls what gets sent back to
the client for its exception types. Don't accidentally leak internals:

```python
@posts.errorhandler(DatabaseError)
async def handle_db_error(request, exc):
    # Log the real exception server-side...
    logger.error(f"DB error: {exc}", exc_info=exc)
    # ...but never put exc's raw message straight into the response.
    return JSONResponse({"error": "Internal error"}, status_code=500)
```

## No unmounting

There's no `app.unmount_module()`. Once mounted, a module's routes stay
registered for the app's lifetime. This is deliberate -- runtime
unmounting of routes is a much larger design problem (in-flight
requests, cache invalidation, route-table consistency) that this cut
doesn't attempt to solve. If you need conditional features, decide
whether to mount a module *before* calling `mount_module()`, not after:

```python
if feature_flags.get("new_dashboard"):
    app.mount_module(dashboard_v2, prefix="/dashboard")
else:
    app.mount_module(dashboard_v1, prefix="/dashboard")
```

## WebSocket routes are handled, but check your version

Flaxon's own `Router.include_router()` re-prefixes HTTP routes
correctly but does **not** re-prefix WebSocket routes at all (verified
against the router source). `modules.py` works around this itself, so
WebSocket routes on a module mount correctly regardless -- but if you
ever bypass `mount_module()` and call `include_router()` directly on a
module's `.router`, you'll hit this gap yourself.

## Route collision warnings are expected and fine

Mounting a module whose routes overlap with an existing catch-all
pattern (e.g. a literal route landing inside a broader `<param>`
pattern from something else, like `AdminDashboard`) will log a
collision warning at mount time. This is informational, not an error --
Flaxon's router resolves these correctly via specificity (literal
segments always win over `<param>` segments, regardless of which was
registered first). Don't be alarmed by a noisy startup log full of
these on an app with several plugins mounted; check that the *specific*
route you care about actually resolves to what you expect, using
`flaxon routes app:app`.

---

# Full example: a real module, everything together

```python
# cli/blog.py
from flaxon import Flaxon
from flaxon.http import JSONResponse, Request
from flaxon.exceptions import Unauthorized
from flaxon.modules import FlaxonModule

class PostNotFound(Exception):
    pass

blog = FlaxonModule("blog", template_dir="templates", static_dir="static")
blog.requires("db")

@blog.before_request
async def require_api_key(request):
    if request.headers.get("x-api-key") != "demo-key":
        raise Unauthorized("Missing API key")

@blog.errorhandler(PostNotFound)
async def handle_missing(request, exc):
    return JSONResponse({"error": str(exc)}, status_code=404)

@blog.get("/posts")
async def list_posts(db):
    return await db.fetch_all("SELECT * FROM posts")

@blog.get("/posts/<int:post_id>")
async def get_post(post_id: int, db):
    post = await db.fetch_one("SELECT * FROM posts WHERE id = ?", post_id)
    if not post:
        raise PostNotFound(f"No post with id {post_id}")
    return post

@blog.get("/")
async def home(request: Request):
    return await request.render("index.html")

@blog.on_startup
async def warm_cache():
    print("Blog module ready.")

@blog.cli_command("seed", help_text="Seed demo blog posts")
async def seed_posts(console):
    console.info("Seeding demo posts...")

blog.install_cli_commands(globals())


# app.py
from flaxon import Flaxon
from cli.blog import blog  # reuse the same module instance defined above

app = Flaxon("blog-app", debug=True)
app.container.register_instance("db", my_database_connection)
app.mount_module(blog, prefix="/blog")
```

```bash
flaxon run app:app --reload   # serves the app
flaxon seed                    # runs the module's own CLI command
flaxon routes app:app          # confirms everything mounted where you expect
```
