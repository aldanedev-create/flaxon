# Learn full-stack Flaxon in ten lessons

For a complete application from CLI generation through deployment, start with the
[Project Manager ebook](project-manager/index.md). The lessons below explain
individual full-stack concepts and remain useful as reference.

Build a Taskboard, then explore other ways to use the same Python application:
interactive Teloce pages, server-rendered Jinax pages, feature modules, API clients
and live interfaces. The lessons use readable Python and TypeScript, explicit
file names and checks you can perform yourself.

**Flaxon** owns HTTP, validation, authentication, persistence integration and
WebSockets. **Teloce** compiles `.html`/`.vel` components and runs their reactive
interface in the browser. **MinifyJS** optimizes production JavaScript. These are
different jobs: TypeScript cannot replace server validation, and a browser router
cannot authorize a database operation.

Start with the [quick start](../quickstart.md). Each lesson explains which files
to change. Code marked as a fragment extends the earlier app; it is not a separate
complete application. The [course example](../../examples/teloce_taskboard/README.md)
provides a runnable `.html` interface with TypeScript helpers. The
[CDN converter](../../examples/teloce_head_ts/README.md) provides a `.vel` variant.

| Lesson | What you learn |
| --- | --- |
| [1. Understand the page lifecycle](01-first-app.md) | Python app, HTML component, build and browser lifecycle |
| [2. Build useful components and scoped styles](02-components.md) | Props, events, slots, directives, scoped CSS and teardown |
| [3. Connect writes to validated Python endpoints](03-typed-api.md) | Typed fetch helpers, validation and readable error handling |
| [4. Use TypeScript without sending types to browsers](04-typescript.md) | Shared types, standalone .ts files and transpilation limits |
| [5. Configure the document head and CDN resources](05-head-and-cdn.md) | Optional metadata, local assets, CDN loading and script ordering |
| [6. Add pages and direct-link navigation](06-routing.md) | Client pages, dynamic parameters, server fallback and Jinax alternative |
| [7. Organize full-stack features with modules](07-modules.md) | Feature modules, routers, services and browser route mapping |
| [8. Persist data and authorize every operation](08-data-and-security.md) | Database transactions, authentication, authorization and uploads |
| [9. Add live updates and test the full boundary](09-live-updates.md) | WebSockets, subscriptions, signals and integration tests |
| [10. Build, deploy and maintain the complete application](10-production.md) | Builds, tasks, API contracts, extensions and deployment |

## Complete reference coverage

Ten lessons teach application patterns; the references below cover the broader
API surface without pretending that every optional integration belongs in one
starter app. Use the relevant guide when adding that capability.

| Flaxon area | Reference | Lesson |
| --- | --- | --- |
| Application, HTTP verbs, response types, static files, lifecycle | [Application](../api/application.md), [HTTP](../api/http.md), [Responses](../guides/responses.md) | 1, 3, 5, 10 |
| Parameters, query/body/form parsing, schemas, Pydantic | [Routing](../api/routing.md), [Requests](../guides/requests.md), [Validation](../api/validation.md), [Pydantic](../guides/pydantic.md) | 3, 8 |
| Modules, routers, services, scaling | [Modules](../guides/Modules.md), [Scaling](../guides/scaling.md) | 7 |
| Jinax, inheritance, macros, filters, templates | [Jinax](../api/jinax.md) | 6 |
| Sessions, JWT, API keys, permissions, middleware, CSRF | [Authentication](../guides/authentication.md), [Authorization](../guides/authorization.md), [Security](../security.md), [Middleware](../guides/middleware.md) | 8 |
| Database adapters, transactions, repositories, migrations | [Databases](../guides/databases.md) | 8 |
| WebSockets, rooms, heartbeat, disconnects | [WebSockets](../api/websocket.md) | 9 |
| Tasks, workers, queues, retries and schedules | [Tasks](../api/tasks.md) | 10 |
| OpenAPI, GraphQL, Admin/CMS | [OpenAPI](../guides/openapi.md), [GraphQL](../api/graphql.md), [Admin](../api/admin.md), [CMS](../api/admin-cms.md) | 10 |
| ASGI mounting, FastMCP, plugins, mobile integrations | [FastMCP](../guides/fastmcp.md), [Plugins](../guides/plugins.md), [Ecosystem](../ecosystem.md) | 10 |
| Testing, debugging, logs, health and metrics | [Testing](../api/testing.md), [Debugging](../guides/debugging.md), [Deployment](../deployment.md) | 9, 10 |

| Teloce area | Lesson | Upstream reference |
| --- | --- | --- |
| .html/.vel components, props, events, slots, imports | 1, 2 | [Components](https://github.com/aldanedev-create/teloce-py/blob/main/docs/components.md) |
| Directives, models, classes, text/HTML binding | 2 | [Syntax](https://github.com/aldanedev-create/teloce-py/blob/main/docs/vel-syntax.md) |
| Data, computed, watch, signals, effects, batching | 2, 9 | [Reactivity](https://github.com/aldanedev-create/teloce-py/blob/main/docs/reactivity.md) |
| TypeScript components and helper modules | 3, 4 | [TypeScript](https://github.com/aldanedev-create/teloce-py/tree/main/docs) |
| Browser pages and routing | 6, 7 | [Flaxon Teloce API](../api/teloce.md) |
| Lifecycle, teardown, runtime modules | 2, 9 | [Runtime](https://github.com/aldanedev-create/teloce-py/blob/main/docs/runtime-reference.md) |
| Scoped CSS, compiler options, assets, production optimization | 2, 5, 10 | [Compiler](https://github.com/aldanedev-create/teloce-py/blob/main/docs/compiler.md), [MinifyJS](https://github.com/aldanedev-create/teloce-py/blob/main/docs/minifyjs.md) |
| Standalone runtime for server HTML, plugins and tooling | 6, 10 | [Standalone](https://github.com/aldanedev-create/teloce-py/blob/main/docs/standalone-runtime.md), [Plugins](https://github.com/aldanedev-create/teloce-py/blob/main/docs/plugins.md) |

TypeScript support depends on the installed Teloce version. Its transpiler removes
supported type syntax; it is not a full semantic type checker. Browser HMR,
automatic SSR and automatic account/database setup are not implied by full-stack.

## Project manager recording course

For a complete backend-first project built from the CLI, follow the [15-chapter project manager ebook](project-manager/index.md). Each step identifies a file to create, a whole-file replacement, or an exact existing block to replace. It includes code, commands, what to say, expected results, troubleshooting and chapter recovery instructions.

The planned recording target is Flaxon 3.0.0 after publication and a clean rehearsal. The ebook keeps that release installation separate from its verified preview wheels. It teaches the current ORM API, Python migrations and management.py workflow without claiming that 3.0.0 is already available.
