# Flaxon documentation

Flaxon brings Python APIs, Teloce interfaces, TypeScript, modules, persistence, and administration into one full-stack application. Teloce compiles your HTML components and browser scripts; Flaxon serves the application and runs its Python features.

## Start here

```bash
python -m pip install "flaxon[standard]"
flaxon new my-project
cd my-project
python -m pip install -e .
python management.py check
python management.py makemigrations
python management.py migrate
python management.py setup-admin
python management.py runserver
```

The default starter welcomes you at `/`, demonstrates a module-owned Python API from TypeScript, and includes a protected `/admin`. Try `/server-page` for the complete Jinax example, and run `flaxon welcome` or `flaxon welcome-status` for module-owned custom commands. Choose Flaxon + Jinax for server-rendered applications, Flaxon + Teloce for interactive interfaces, or combine them. There is no default administrator password. Read [getting started](getting-started.md) for virtual environments, project files, command details, and deployment boundaries.

## A complete learning path

1. **Build the server:** [routing](guides/routing.md), [requests](guides/requests.md), [validation](guides/validation.md), [databases](guides/databases.md), and [authentication](guides/authentication.md).
2. **Build the interface:** [Teloce SPA](guides/Teloce-Spa.md), [HTML components](fullstack/02-components.md), [typed APIs](fullstack/03-typed-api.md), and [TypeScript](fullstack/04-typescript.md).
3. **Organize features:** [modules](guides/Modules.md), [navigation](fullstack/06-routing.md), and [admin/CMS](guides/admin-cms.md).
4. **Ship responsibly:** [testing](guides/testing.md), [security](security.md), [production](fullstack/10-production.md), and [deployment](deployment.md).

## Build a complete project manager

Follow the [copy-and-paste ebook course](fullstack/project-manager/index.md).
Start with `flaxon new project_manager`, then build working authentication,
owned projects, tasks, a Teloce HTML SPA with scoped CSS and signals, staff Admin,
CMS help content, tests and Render deployment. Every chapter names the files to
create or replace and includes the complete code and verification commands.

## Ten full-stack concept lessons

Work through [the course overview](fullstack/index.md), then follow these lessons:

- [Lesson 1: Understand the page lifecycle](fullstack/01-first-app.md)
- [Lesson 2: Build useful components and scoped styles](fullstack/02-components.md)
- [Lesson 3: Connect writes to validated Python endpoints](fullstack/03-typed-api.md)
- [Lesson 4: Use TypeScript without sending types to browsers](fullstack/04-typescript.md)
- [Lesson 5: Configure the document head and CDN resources](fullstack/05-head-and-cdn.md)
- [Lesson 6: Add pages and direct-link navigation](fullstack/06-routing.md)
- [Lesson 7: Organize full-stack features with modules](fullstack/07-modules.md)
- [Lesson 8: Persist data and authorize every operation](fullstack/08-data-and-security.md)
- [Lesson 9: Add live updates and test the full boundary](fullstack/09-live-updates.md)
- [Lesson 10: Build, deploy and maintain the complete application](fullstack/10-production.md)

## Complete documentation directory

Use the guides for explanations, the API pages for reference, and the examples for working patterns. The directory below lists every Markdown document in this documentation tree, including older lessons and editor guides.

### Foundations and operations

- [Flaxon Admin Dashboard Guide](admin-guide.md)
- [Architecture](architecture.md)
- [Flaxon & Plugins - Quick Reference Cheat Sheet](cheatsheet.md)
- [Flaxon CMS](cms.md)
- [Configuration](configuration.md)
- [Contributing to Flaxon](contributing.md)
- [Deployment](deployment.md)
- [Flaxon ecosystem](ecosystem.md)
- [Getting started](getting%20Starting.md)
- [Getting started with Flaxon](getting-started.md)
- [GraphQL API Example](graphql.md)
- [Installation](installation.md)
- [Email](mail.md)
- [Maintenance Guide](maintenance.md)
- [Migration Guide](migration-guide.md)
- [Performance](performance.md)
- [Philosophy](philosophy.md)
- [Full-stack quick start](quickstart.md)
- [Security](security.md)
- [Flaxon Technical Passport](tech-passport.md)
- [Flaxon Update Policy](updates.md)

### Feature guides

- [Admin and CMS Production Guide](guides/admin-cms.md)
- [Declarative admin resources](guides/admin-resources.md)
- [Metrics and dashboard cards](guides/admin-metrics.md)
- [Admin actions](guides/admin-actions.md)
- [Filters, lenses and safety](guides/admin-filters-and-safety.md)
- [Admin extensions with Teloce](guides/admin-extensions.md)
- [Flaxon Admin in Production](guides/admin-production.md)
- [Authentication](guides/authentication.md)
- [Request performance and authentication migration](guides/request-security-upgrade.md)
- [Authorization](guides/authorization.md)
- [Databases](guides/databases.md)
- [Debugging](guides/debugging.md)
- [FastMCP Integration](guides/fastmcp.md)
- [GraphQL API Example](guides/graphql.md)
- [Jinax Templates](guides/jinax.md)
- [Admin and CMS with microservices](guides/microservices.md)
- [Middleware](guides/middleware.md)
- [Mobile Development](guides/mobile-developement.md)
- [Modules Guide](guides/Modules.md)
- [OpenAPI, Swagger UI, and ReDoc](guides/openapi.md)
- [Project templates](guides/project-templates.md)
- [Plugins](guides/plugins.md)
- [Optional Teloce plugins: PWA, forms, i18n, accessibility and head](guides/teloce-first-party-plugins.md)
- [Pydantic Integration](guides/pydantic.md)
- [Requests](guides/requests.md)
- [Responses](guides/responses.md)
- [Routing](guides/routing.md)
- [Growing a Flaxon application](guides/scaling.md)
- [Tasks](guides/tasks.md)
- [Teloce Spa](guides/Teloce-Spa.md)
- [Teloce SSR and browser debugging](guides/teloce-ssr-debugging.md)
- [Testing](guides/testing.md)
- [Validation](guides/validation.md)
- [WebSockets](guides/websockets.md)

### API reference

- [Admin and CMS API Reference](api/admin-cms.md)
- [Admin API Reference](api/admin.md)
- [Admin extension API](api/admin-extensions.md)
- [Application API](api/application.md)
- [GraphQL API Reference](api/graphql.md)
- [HTTP API](api/http.md)
- [Jinax API](api/jinax.md)
- [Routing API](api/routing.md)
- [Security API](api/security.md)
- [Tasks API](api/tasks.md)
- [Teloce full-stack integration: API reference](api/teloce.md)
- [Testing API](api/testing.md)
- [Validation API](api/validation.md)
- [WebSocket API](api/websocket.md)

### Full-stack course

- [Lesson 1: Understand the page lifecycle](fullstack/01-first-app.md)
- [Lesson 2: Build useful components and scoped styles](fullstack/02-components.md)
- [Lesson 3: Connect writes to validated Python endpoints](fullstack/03-typed-api.md)
- [Lesson 4: Use TypeScript without sending types to browsers](fullstack/04-typescript.md)
- [Lesson 5: Configure the document head and CDN resources](fullstack/05-head-and-cdn.md)
- [Lesson 6: Add pages and direct-link navigation](fullstack/06-routing.md)
- [Lesson 7: Organize full-stack features with modules](fullstack/07-modules.md)
- [Lesson 8: Persist data and authorize every operation](fullstack/08-data-and-security.md)
- [Lesson 9: Add live updates and test the full boundary](fullstack/09-live-updates.md)
- [Lesson 10: Build, deploy and maintain the complete application](fullstack/10-production.md)
- [Learn full-stack Flaxon in ten lessons](fullstack/index.md)

### Worked examples

- [Android Backend Example](examples/android-Development.md)
- [Basic API Example](examples/basic-api.md)
- [CMS Example](examples/cms/admin-cms/example-cms.md)
- [Full Admin and CMS Example](examples/cms/full_admin_cms/README.md)
- [FastMCP Example](examples/fastmcp-app.md)
- [Frontend Integration Examples](examples/frontend-integration.md)
- [GraphQL Example](examples/grahql/readme.md)
- [Jinax Website Example](examples/jinax-website.md)
- [Large Application Example](examples/large-application.md)
- [Mail Example](examples/mail/readme.md)
- [Modules Example: Catalog and Orders](examples/Modules/readme.md)
- [OpenAPI API Example](examples/openapi.md)
- [Pydantic API Example](examples/pydantic-api.md)
- [React frontend and API](examples/react-backend.md)
- [Flaxon + React example](examples/react_backend/README.md)
- [School portal: Admin plus Flaxon modules](examples/school-portal.md)
- [WebSocket Chat Example](examples/websocket-chat.md)
- [Flaxon WhatsApp-style Chat](examples/whatsapp_chat/README.md)

### Additional lessons and cheat sheets

- [Admin and CMS Cheat Sheet](lessons/Admin%20cheatsheet.md)
- [Building Flaxon Plugins](lessons/Building%20Flaxon%20Plugins.md)
- [CLI Reference](lessons/Cli.md)
- [Flaxon Features](lessons/Features.md)
- [Flaxon Cheat Sheet](lessons/Flaxon%20Cheat%20Sheet.md)
- [Industrial Admin Customization](lessons/Industrial%20Admin%20Customization.md)
- [Deploying Flaxon Apps](lessons/Platform-Deployment.md)
- [Building a Production App with Modules](lessons/production-app-guide.md)
- [Teloce Integration Reference](api/teloce.md)
- [Flaxon VS Code Extension Cheat Sheet](lessons/vscode%20Cheatsheet.md)

### AI-facing docs (generated)

- [Tutorial ladder](tutorial-ladder.md)
- [Cookbook](cookbook.md)
- [Verified pitfalls](ai/pitfalls.md)
- [AI API reference](ai/api-reference.md)
- [Recipe: minimal API](ai/recipes/api.md)
- [Recipe: database](ai/recipes/database.md)
- [Recipe: admin resource](ai/recipes/admin-resource.md)
- [Recipe: metric](ai/recipes/metric.md)
- [Recipe: action](ai/recipes/action.md)
- [Recipe: Teloce field](ai/recipes/teloce-field.md)
- [Recipe: WebSocket room](ai/recipes/websocket-room.md)

### Internal

- [Production Readiness Audit](internal/production-audit.md)

### VS Code extension

- [Flaxon VS Code Extension - Advanced Guide](vs%20Code%20%28Extension%29/advanced.md)
- [Flaxon VS Code Extension - Features Guide](vs%20Code%20%28Extension%29/features.md)
- [Flaxon VS Code Extension - Getting Started](vs%20Code%20%28Extension%29/getting-started.md)
- [Flaxon VS Code Extension - Quick Cheat Sheet](vs%20Code%20%28Extension%29/Quick%20Cheat%20Sheet.md)

- [ORM, settings, and management commands](guides/orm.md)
- [ORM Admin custom pages](guides/orm-admin-custom-pages.md)

- [01 | Preview and CLI setup](fullstack/project-manager/01.md)

- [02 | Settings, management and application composition](fullstack/project-manager/02.md)

- [03 | Models and Python migrations](fullstack/project-manager/03.md)

- [04 | Customer authentication and sessions](fullstack/project-manager/04.md)

- [05 | Owned project APIs](fullstack/project-manager/05.md)

- [06 | Task workflow](fullstack/project-manager/06.md)

- [07 | Backend tests](fullstack/project-manager/07.md)

- [08 | Teloce HTML shell and scoped CSS](fullstack/project-manager/08.md)

- [09 | Login and project screens](fullstack/project-manager/09.md)

- [10 | Task components, signals and progress](fullstack/project-manager/10.md)

- [11 | SPA routing and direct refresh](fullstack/project-manager/11.md)

- [12 | Staff Admin](fullstack/project-manager/12.md)

- [13 | CMS help and sample data](fullstack/project-manager/13.md)

- [14 | Full-stack verification](fullstack/project-manager/14.md)

- [15 | Production build and Render](fullstack/project-manager/15.md)

- [JSON serialization and migration](guides/json-serialization.md)

- [Release readiness audit](releases/readiness-audit.md)

- [Routing and quality audit](quality-audit.md)

- [16 | PWA: installation, offline fallback and updates](fullstack/project-manager/16.md)

- [Type-check Teloce interfaces](guides/typecheck.md)

- [Publishing releases](publishing.md)

## Tutorial: Discord clone and bot platform

- [Discord clone tutorial overview](tutorials/discord-clone/index.md)
  - [Lesson 1 — Overview: the system you are about to build](tutorials/discord-clone/01-overview.md)
  - [Lesson 2 — Scaffold the app with `flaxon new`](tutorials/discord-clone/02-scaffold.md)
  - [Lesson 3 — The data model and migrations](tutorials/discord-clone/03-data-model.md)
  - [Lesson 4 — App context and dependency injection](tutorials/discord-clone/04-context-and-di.md)
  - [Lesson 5 — Authentication](tutorials/discord-clone/05-authentication.md)
  - [Lesson 6 — Servers, channels, and permissions](tutorials/discord-clone/06-servers-channels.md)
  - [Lesson 7 — Messages: durable history and cursor pagination](tutorials/discord-clone/07-messages.md)
  - [Lesson 8 — Bot tokens and slash commands](tutorials/discord-clone/08-bot-tokens-commands.md)
  - [Lesson 9 — Bot events: subscriptions, idempotency, retries](tutorials/discord-clone/09-bot-events.md)
  - [Lesson 10 — Realtime: ChannelHub and the WebSocket module](tutorials/discord-clone/10-realtime-hub.md)
  - [Lesson 11 — Multi-worker: making realtime survive more than one process](tutorials/discord-clone/11-multi-worker.md)
  - [Lesson 12 — Flaxon Admin: moderation without custom CRUD](tutorials/discord-clone/12-admin.md)
  - [Lesson 13 — CMS: an editorial layer beside the app data](tutorials/discord-clone/13-cms.md)
  - [Lesson 14 — The SPA: types, API client, and app shell](tutorials/discord-clone/14-spa.md)
  - [Lesson 15 — Wiring the UI: components and the WebSocket layer](tutorials/discord-clone/15-wiring-ui.md)
  - [Lesson 16 — Security review: audit what you actually built](tutorials/discord-clone/16-security.md)
  - [Lesson 17 — Seed it and run it](tutorials/discord-clone/17-seed-and-run.md)
  - [Lesson 18 — Testing the whole system](tutorials/discord-clone/18-testing.md)
  - [Lesson 19 — Deployment and hardening](tutorials/discord-clone/19-deployment.md)
