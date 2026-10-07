# Teloce full-stack integration: API reference

Flaxon owns HTTP, APIs and WebSockets. Teloce compiles UI components and handles
browser state and navigation. MinifyJS optimizes generated production JavaScript;
it does not execute requests or replace Teloce's compiler.

## API reference

### `app.use_teloce(...)`

Register once, before application startup. Returns `Teloce` and exposes it as
`app.teloce`.

| Argument | Default | Purpose |
| --- | --- | --- |
| `project_root` | Current directory | Root containing every UI source |
| `ui_dir` | `ui` | Application components and pages |
| `build_dir` | `.flaxon/build` | Generated output, relative to project root |
| `static_url` | `/_flaxon` | Browser URL serving generated files |
| `entry` | `app.html` | Root component within a registered UI tree |
| `title` | Application name | HTML document title |
| `options` | `{}` | Overrides passed to Teloce Builder; also `spa_mode`/`spa_base` |

Startup compiles sources. Missing directories, invalid components and duplicate
page routes fail the build. UI directories must be within `project_root`.

### `await request.compile(entry="app.html", context=None, title=None)`

Returns an `HTMLResponse` shell importing the root component, styles and router.
Context is safely serialized as JSON and passed to `mount()`. This is client-side
rendering, not server-rendered component HTML. A cached startup build is reused;
if none exists, the integration builds lazily. Configure `app.use_teloce()` first.
Never put secrets in context: it is visible in the browser.

### `app.teloce.build()` and `register_source(name, directory, routes=None)`

`build()` explicitly rebuilds registered trees and returns Teloce's result.
`register_source()` adds a source and invalidates the cached build. Names and
source directories must be unique. Register before serving traffic; runtime
concurrent builds are not a deployment strategy.

### `FlaxonModule(name, ui_dir=..., ui_routes=...)`

Mounting a module registers its backend endpoints and UI source. It works before
or after `use_teloce()`. `ui_routes` maps generated page filenames to client paths,
for example `{"ProductDetails/[id].js": "/products/:id"}`. Backend mount prefixes
such as `/api/catalog` do not automatically prefix browser page routes.

### Navigation attributes

`data-teloce-router-view` identifies the page outlet (or use `id="router-view"`).
`data-teloce-link` marks an anchor for client navigation:

```html
<a href="/jobs" data-teloce-link>Jobs</a>
<main data-teloce-router-view></main>
```

The listener only intercepts ordinary same-origin HTTP(S) clicks to a matching
client route. External links, modified clicks, downloads, other targets,
nonmatching routes and same-page fragments retain browser behavior. Router guards
can reject a matched navigation; it does not fall back to a full page load.
The server still needs a catch-all route for direct visits and page refreshes.

## Lesson 1: Compile your first interface

Install `flaxon[standard]` and a Teloce version containing its MinifyJS integration.
For repository development, install Flaxon and updated Teloce from their actual
local checkouts; do not copy another developer's Windows path.

Create `ui/app.html`:

```html
<template><h1>{{ business }}</h1></template>
<script>export default { props: ["business"] };</script>
```

Create `app.py`:

```python
from pathlib import Path
from flaxon import Flaxon, Request

app = Flaxon("My business", debug=True)
app.use_teloce(project_root=Path(__file__).parent, ui_dir="ui")

@app.get("/")
async def home(request: Request):
    return await request.compile("app.html", {"business": "Morgan Build & Repair"})
```

Run `flaxon run app:app --reload` and visit port 8000. The component is compiled
as HTML-mode Teloce input, not served as raw HTML. `.vel` components are also
supported by Teloce. Edit a source and refresh after the server restarts.
Generated `.flaxon` files are excluded from the watcher; `.vel` files are included.
This process reload is not browser HMR.

## Lesson 2: Load data from Flaxon

Add an API before your catch-all route:

```python
@app.get("/api/jobs")
async def jobs():
    return {"items": [{"id": 1, "customer": "Harbour View Bakery"}]}
```

A page can fetch it after mounting:

```html
<template><p v-for="job in jobs" :key="job.id">{{ job.customer }}</p></template>
<script>
export default {
  data() { return { jobs: [] }; },
  async mounted() {
    const response = await fetch("/api/jobs");
    if (!response.ok) throw new Error("Could not load jobs");
    this.jobs = (await response.json()).items;
  }
};
</script>
```

The shipped SiteLedger Jobs page adds loading state, a Refresh button and a
reusable `JobCard`. Its in-memory API is a teaching fixture: add persistence,
authorization and visible loading/error states for production.

## Lesson 3: Add page navigation

Put pages in `ui/pages/`; `Jobs.html` becomes `/jobs` and `jobs/[id].html` becomes
`/jobs/:id`. Put marked links and a router outlet in `app.html`.
Add a server fallback after API routes:

```python
@app.get("/")
@app.get("/<path:spa_path>")
async def page(request: Request, spa_path: str = ""):
    return await request.compile("app.html", {"business": "My business"})
```

The browser router mounts pages; Flaxon handles `/api/...` data. Directly visiting
`/jobs/1` returns the same shell, and the router reads the URL. SiteLedger's detail
page receives `id` as a prop and fetches `/api/jobs/${this.id}`.

## Lesson 4: Keep a feature in one module

```python
from pathlib import Path
from flaxon.modules import FlaxonModule

catalog = FlaxonModule(
    "catalog", ui_dir=Path(__file__).parent / "ui",
    ui_routes={"ProductDetails/[id].js": "/products/:id"},
)

@catalog.get("/products")
async def products():
    return {"items": []}

# In the application:
app.mount_module(catalog, prefix="/api/catalog")
```

See the modules shop for auth, catalog, orders and chat. Catalog owns pages and
product components; chat owns a WebSocket and its page. Its browser component
closes the socket in `beforeUnmount()`. Duplicate page routes across modules fail
rather than silently choosing one. The sample login/data are demonstrations,
not a complete security or database implementation.

## Lesson 5: Deploy with MinifyJS

Use `debug=False`. Flaxon requests production compilation, asset hashes and
extracted CSS. Updated Teloce uses MinifyJS for component/runtime optimization;
Flaxon also optimizes its separately generated router through MinifyJS. Both
compression and local-name mangling are enabled for that router. No Node is needed.

Development keeps Teloce's existing pipeline and source maps. This change does
not enable the experimental native development backend. Bundling is not enabled
by default; it requires selecting an appropriate entry and testing all module
pages/lazy imports. Do not assume the startup integration is a unified bundle.

The build directory is served with `Cache-Control: no-cache` in both modes, so
stable aliases and `router.js` revalidate after deployment. The HTML shell uses
`no-cache` in production and `no-store` in development. A CDN must preserve this
policy; only add long immutable caching to files with verified content hashes.

Install pinned compatible versions, build in a writable location at startup,
and deploy source plus dependencies (or arrange an explicit build lifecycle).
Each worker currently builds on startup: avoid concurrent writes to a shared
build directory by using a single builder or isolated worker output directories.
Add real authentication, database storage and authorization for business data.

[SiteLedger example](../../examples/teloce_siteledger/README.md) ·
[Modules example](../../examples/teloce_modules_shop/README.md)

## Optional page-head configuration

All additions are optional; existing `title`-only applications continue working.

```python
app.mount_static("/static", str(project_root / "public"))
theme_cdn = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
app.use_teloce(
    project_root=project_root, ui_dir="ui", title="Taskboard",
    favicon="/static/favicon.svg", description="Team tasks in one place.",
    lang="en", theme_color="#101827", stylesheets=[theme_cdn],
    scripts=[{"src": "/static/help.js", "defer": True}],
)
```

| Option | Default | Meaning |
| --- | --- | --- |
| `favicon` | None | Icon link URL; serve the file separately |
| `description` | None | Escaped description meta content |
| `lang` | `en` | Escaped HTML document language, not script language |
| `theme_color` | None | Theme-color meta content |
| `stylesheets` | None | Ordered strings or dictionaries containing `href` |
| `scripts` | None | Ordered strings or dictionaries containing `src` |

Scripts support `type`, boolean `defer`/`async`, `integrity`, `crossorigin`,
`referrerpolicy`. Stylesheets support `rel`, `type`, `media`, `sizes`, `integrity`,
`crossorigin`, `referrerpolicy`. Resource URLs allow relative, HTTP and HTTPS
URLs; executable/data schemes and unknown attributes are rejected. Values are
escaped; arbitrary HTML/event-handler attributes are not accepted.

These settings add tags to the head; they do not download, bundle or upload CDN
resources. Pin trusted dependencies. Scripts execute with page privileges.
Use verified SRI hashes and `crossorigin="anonymous"` where supported; don't
invent hashes. Async resources have no guaranteed execution order. Do not assume
an external library has loaded before a component mounts: coordinate explicitly
if your component depends on it. Fonts and resources may require network access
and disclose requests to providers. Local copies support offline applications.

Generated component CSS precedes extra stylesheet links, allowing intentional
external overrides. Deferred classic scripts retain their order with each other;
module and async timing needs separate consideration. The integration still
emits an inline module bootstrap; a strict CSP needs a compatible nonce/hash
strategy beyond these resource attributes. A favicon does not configure native
Windows icons. Manifest and arbitrary head HTML are not part of this API.

For TypeScript, use `<script lang="ts">` and import `.ts` helpers with a compatible
Teloce version. Output is JavaScript; transpilation does not replace type checking.
See the [tested example](../../examples/teloce_head_ts/README.md) and
[10 full-stack lessons](../fullstack/index.md).
