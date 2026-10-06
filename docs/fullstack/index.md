# Ten lessons: build a full-stack Taskboard with Flaxon

Flaxon provides the Python server and application lifecycle. Teloce is the
component compiler and browser runtime: it turns `.html`/`.vel` components into
JavaScript, manages reactive UI state, and supplies client navigation. MinifyJS
optimizes production JavaScript. Your application supplies business rules,
authorization and persistence.

These lessons build on the [runnable quick start](../quickstart.md). Code fragments
extend that project; the complete TypeScript/CDN teaching application is
[provided separately](../../examples/teloce_head_ts/README.md). Read lessons in
order. Each checkpoint is a practical check, not a claim that every fragment is
a complete production application.

## 1. Understand the page lifecycle

Create the quick-start files and run the development server. `app.use_teloce()`
registers the UI tree and startup build. `request.compile()` returns an HTML
shell referencing the built component and styles. The browser mounts the
component, then its `mounted()` callback requests `/api/tasks`.

The template source is not simply returned as an HTML page. The integration is
client rendering: the initial body contains a mount point rather than rendered
task rows. If a page needs server-rendered HTML, use Flaxon's Jinax integration
and `request.render()`. Choose rendering according to the page's requirements.

Keep browser-only UI behavior inside components and privileged business work
inside Python endpoints. Context passed to `compile()` is serialized into the
page: it is suitable for public display values, never credentials.

**Checkpoint:** inspect page source and Network tools. Find the mount point,
compiled `.js`, stylesheet and API request. Disable JavaScript to understand
which content depends on the browser runtime.

## 2. Build useful components and scoped styles

Start with loading, success, empty and failure states. The quick-start component
already handles a failed API request; add a retry button that invokes a shared
`loadTasks` method rather than duplicating fetch logic. Preserve current rows
when refreshing so a temporary failure does not erase the user's context.

Extract a row into `ui/components/TaskRow.html` when it has a distinct job:

```html
<template><article><h2>{{ title }}</h2><p>{{ status }}</p></article></template>
<script>export default { props: ["title", "status"] };</script>
<style scoped>article { padding: 1rem; border: 1px solid #bbb; }</style>
```

Import it from the parent component and register it through Teloce's component
API; see the existing [SiteLedger components](../../examples/teloce_siteledger).
Scoped CSS limits component styling, while shared typography belongs in the
application shell. Use real labels, buttons, visible focus and status regions.
Do not make a clickable `div` the only way to perform an action.

**Checkpoint:** show zero tasks, a failed request and a populated list. Navigate
with the keyboard. Confirm a row's styles do not unexpectedly affect another
page. Component extraction should clarify responsibilities rather than create
one file for every line of markup.

## 3. Connect writes to validated Python endpoints

The browser should send a small JSON payload; the server should decide whether
it is acceptable. For the teaching fixture, use an in-memory list:

```python
from flaxon.http import JSONResponse

items = []

@app.post("/api/tasks")
async def create_task(request: Request):
    try:
        data = await request.json()
    except ValueError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    title = data.get("title") if isinstance(data, dict) else None
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
        return JSONResponse({"error": "Title must contain 1–200 characters"}, status_code=422)
    task = {"id": len(items) + 1, "title": title.strip()}
    items.append(task)
    return JSONResponse(task, status_code=201)
```

Update the GET endpoint to return `items`. In the component, POST with
`Content-Type: application/json`, check `response.ok`, display the error and
clear the input only after success. Disable repeated submission while waiting.
In-memory IDs and storage are teaching fixtures and unsuitable for concurrent
production workers.

Use Flaxon's [validation guide](../guides/validation.md) for reusable schemas.
Client validation improves usability; server validation protects the API.
**Checkpoint:** submit an empty title, malformed JSON and a valid title. Check
status codes and verify that failed submissions leave the user's input intact.

## 4. Use TypeScript without sending types to browsers

Move shared calculations or transformations into `.ts` modules:

```ts
// ui/task-label.ts
export function taskLabel(title: string, complete: boolean): string {
  return complete ? `${title} — complete` : title;
}
```

Import the helper inside `<script lang="ts">` in a `.vel` component. Teloce
transpiles supported type syntax and rewrites `.ts` imports to emitted `.js`.
The Python head option `lang="en"` has a different purpose: it declares the
human language of the HTML document.

The [converter example](../../examples/teloce_head_ts) exercises exactly this
path with `units.ts`. Use a Teloce release containing that support. Supported
syntax is not every TypeScript construct; do not assume enums, namespaces or
parameter properties work in the pure-Python transpiler. Transpilation also
isn't semantic type checking. A separate type-checking tool can be part of CI
when the project's requirements warrant it.

**Checkpoint:** build and inspect the helper output. There should be no type
annotation, `.ts` import or TypeScript served to the browser. Introduce a syntax
error and confirm the build reports it instead of silently shipping bad code.

## 5. Configure the document head and CDN resources

Keep metadata in Python and application markup in Teloce:

```python
app.mount_static("/static", str(project_root / "public"))
app.use_teloce(
    project_root=project_root, title="Taskboard", ui_dir="ui",
    favicon="/static/favicon.svg", description="Track your team's tasks.",
    lang="en", theme_color="#101827",
    stylesheets=["https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"],
    scripts=[{"src": "/static/help.js", "defer": True}],
)
```

All extra settings are optional. The local icon must exist under the static
mount. Resource configuration emits links; it does not copy resources or put
your build on a CDN. Extra stylesheets follow compiled CSS, so inspect overrides.
CDN scripts have page privileges: use trusted providers, pin versions and
verified SRI attributes where practical. Do not load a second Teloce runtime.

Avoid relying on an async script being ready in `mounted()`. Coordinate library
readiness explicitly or use a bundled/local module when it is essential.
For offline desktop applications, ship local fonts and assets. CSP also needs
to account for the generated inline module bootstrap.

**Checkpoint:** inspect head tags, load the favicon, then disconnect networking.
Confirm which external enhancements fail and that the core workflow remains
usable. See the [resource attribute reference](../api/teloce.md).

## 6. Add pages and direct-link navigation

Create `ui/pages/Tasks.html` and `ui/pages/tasks/[id].html`. The integration
builds a shared browser router; dynamic parameters become page props. Use a
root shell with marked links and an outlet:

```html
<nav><a href="/tasks" data-teloce-link>Tasks</a></nav>
<main data-teloce-router-view></main>
```

The root shell mounts the router; a detail page fetches its data by the `id`
prop. Register a server fallback after API routes:

```python
@app.get("/")
@app.get("/<path:spa_path>")
async def page(request: Request, spa_path: str = ""):
    return await request.compile("app.html")
```

Use an explicit API not-found response for unknown API paths so a catch-all
does not turn an API typo into a successful HTML response. External links,
downloads and modified clicks should retain normal browser behavior. Browser
navigation guards improve flow but cannot enforce server authorization.

**Checkpoint:** navigate to a detail page, refresh it, paste its address into a
new tab, and use Back/Forward. A route that only works after clicking inside the
app is missing server fallback behavior. Test unknown API and client paths too.

## 7. Organize full-stack features with modules

Group tasks with their endpoints and UI rather than splitting the entire
project into unrelated frontend/backend repositories:

```python
from flaxon.modules import FlaxonModule

tasks = FlaxonModule("tasks", ui_dir=project_root / "modules/tasks/ui")

@tasks.get("/tasks")
async def list_tasks():
    return {"items": []}

app.mount_module(tasks, prefix="/api")
```

Mounting registers backend routes and the module's UI source. Directories must
remain inside the configured project root. Module names and UI roots must be
unique. A backend prefix does not automatically change browser page routes;
use `ui_routes` when a client route requires an explicit mapping.

Keep repository/data services separate from request handlers so a module can
be tested with a fixture service. Share a small design-system component library
instead of copying markup into every feature. Register sources before serving
traffic; concurrent runtime builds are not a deployment lifecycle.

**Checkpoint:** add a second module and verify both backend endpoints and browser
pages work. Deliberately introduce a duplicate client route and confirm the
build rejects it. See the [modules shop](../../examples/teloce_modules_shop).

## 8. Persist data and authorize every operation

Replace the in-memory list with SQLite for a small deployment or another
supported database for larger workloads. Use database-generated identifiers,
transactions and migrations. Do not block the ASGI event loop with slow
synchronous file or database work; use an async adapter or controlled thread
execution. Read the [database guide](../guides/databases.md) for actual adapter
and lifecycle APIs.

For accounts, choose sessions or another documented authentication mechanism.
Every task query must enforce ownership/team membership on the server, including
read, update and delete. A hidden UI button is not authorization. Context and
browser storage are user-visible, so never send server secrets to components.
Cookie-based authenticated mutations need appropriate CSRF protection and
secure cookie policy; consult the [security guide](../security.md).

Keep validation, authorization and the database write in a coherent operation.
Return an intentional not-found/forbidden response without leaking another
user's records. Separate user-facing errors from internal diagnostic details.

**Checkpoint:** create records for two accounts. Try accessing each record with
the other account, restart the application to check persistence, and provoke a
failed write to ensure the transaction rolls back.

## 9. Add live updates and test the full boundary

Use a Flaxon WebSocket endpoint for task changes when polling is insufficient.
Consult the [WebSocket guide](../guides/websockets.md) for its concrete API.
Authenticate the connection, authorize room membership and validate incoming
messages. A successful HTTP login does not automatically authorize every room.

The Teloce component opens the socket after mounting and closes it in
`beforeUnmount()`. Show disconnected state, retry with bounded backoff, and
refetch canonical data after reconnecting. A broadcast is a notification;
the durable database remains the source of truth.

Use `TestClient` for endpoint behavior and a real browser for component behavior.
The head/TypeScript integration tests build the example and request generated
assets, but browser tests are still needed for library timing and interaction.
Test successful updates, rejected writes, unknown routes, escaping, empty lists
and offline states. Avoid asserting only that HTML returns 200.

**Checkpoint:** open two browser windows, update a task in one, disconnect and
reconnect the other, then navigate away and check that its old socket closes.
Use fixtures and deterministic waits rather than arbitrary long sleeps.

## 10. Build, deploy and maintain the complete application

Set `debug=False` for deployment. Flaxon requests production Teloce compilation,
asset hashes and extracted CSS; MinifyJS optimizes generated JavaScript and the
router. Bundling is an explicit choice, not automatically enabled for every
project. Test lazy pages and shared modules before selecting a bundle entry.

Startup needs a writable build directory. Multiple workers currently build at
startup, so isolate their output directories or arrange a single build lifecycle
instead of concurrent writes. Keep stable aliases and router assets revalidated;
only apply immutable caching to verified content-hashed files. The integration
uses no-cache for assets and production HTML.

Deploy through the [deployment guide](../deployment.md), with HTTPS, trusted
hosts, environment-held secrets, persistent database storage, backups and logs.
Pin and review dependencies. CDN resource URLs are separate from your own asset
deployment; changing `static_url` does not upload your compiled files.

Flaxon's full-stack positioning describes the integrated Python/Teloce workflow.
It does not imply automatic SSR, HMR, authentication, hosting or database setup.
Those choices remain explicit and documented.

**Checkpoint:** test a production build, deep-link refresh, failed API requests,
missing CDN access and a process restart. Restore a backup in a test environment
before relying on the production backup plan.
