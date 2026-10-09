# Changelog

## Unreleased

- Release readiness: preserve environment secret strings, repair version/changelog/artifact/tag tooling, support prerelease versions, verify installed wheels, and make CDN browser tests reproducible.

- Use browser-safe orjson encoding by default; add explicit legacy response and settings modes. See [migration rules](docs/guides/json-serialization.md).
- Parse request headers, cookies, and query parameters lazily.
- Prepare dependency names once and order route candidates during registration.
- Fix dynamic method fallback when a static path exists for another method.

- Avoid session storage and cookies for untouched requests; prepare endpoint arguments at registration while resolving dependencies per request.
- Infer and validate scalar query parameters, returning 422 for invalid input and documenting them in OpenAPI.
- Replace custom JWT signing with PyJWT, require expiry and support configured issuer/audience and trusted key rotation. Legacy tokens require sign-in again.
- Default to Argon2id, retain legacy PBKDF2 verification, upgrade Admin hashes after successful login, and default explicit session cookies to Secure.
- Surface isolated plugin failures, propagate unexpected auth/permission errors, fix compression ASGI handling and missing imports, and repair the mypy platform setting.

## [0.2.7]

- Project CLI: discover commands once, avoid importing project commands for new/version, flush setup messages, show environment progress and stop after a 120-second timeout with recovery instructions.
- Admin/CMS: distinguish the ORM lifecycle object from legacy SQL adapters so generated ORM applications use their metadata store without page errors.
- Documentation: shared settings/management/ORM workflow and a verified 15-chapter, complete-code project-manager ebook covering Teloce HTML, scoped CSS, signals, SPA routing, staff Admin/CMS and Render.



- Bundle Alpine.js for essential Admin/CMS interactions.
- Add permission-filtered relationship selectors, many-to-many forms, optional
  child inlines, query scoping, field groups and custom widget templates.
- Make ORM imports transactional, show field validation errors, reject stale ORM
  edits, preview dependent deletion and enforce cascade delete permissions.
- Add opt-in ORM Admin/CMS metadata storage with Python migrations and a
  transactional legacy SQLite store copy command.

- Integrate pinned Tortoise ORM through flaxon.db and shared typed settings.
- Add model-driven Python migrations and project management commands; preserve legacy adapters/JSON runners.
- Discover model/Admin metadata from explicitly mounted modules without frontend compilation in management mode.
- Add ORM Admin CRUD, typed fields, bounded relationships, validation and project registry isolation.
- Repair disabled-feature navigation and expired/shared-worker CSRF handling in new starters.
- Enforce model/object permissions in global search, exports and bulk actions; redact credentials in snapshots.
- Require CMS authentication by default and publishing rights across writes/imports/restores; support async authorization.


## 2.6

- Add synchronous and asynchronous module-owned starter commands, exposed through project CLI discovery.
- Refresh the welcome page with an installation-success design, hosted Flaxon logo and website links, and a working Jinax page alongside Teloce. Explain both complete-app options in the generated README and getting-started guide.

- Default `flaxon new` to a modular Teloce full-stack welcome application with TypeScript, scoped styles, a module API, persistent protected admin, and project-local migration/admin commands. Keep `--template basic` available.
- Package the starter assets in Flaxon distributions and correct the generated Flaxon dependency name.
- Add a canonical getting-started guide and a complete documentation directory.

## 2.6 — Readable full-stack course

- Shorten the README around Python server and Teloce browser development, keeping the logo.
- Split the full-stack course into ten numbered lesson files with navigation and API coverage maps.
- Add a runnable typed Taskboard using HTML components, TypeScript helpers, validation and reusable components.
- Add compilation/API and browser tests for the Taskboard.


## 2.6 — Full-stack page configuration

- Add optional favicon, description, language, theme color, stylesheet and script settings to Teloce page shells.
- Escape head values and validate resource schemes and supported attributes.
- Add a TypeScript/CDN converter example and integration coverage.
- Position Flaxon as a Python full-stack framework; add a full-stack quick start and ten lessons.


All notable changes to Flaxon will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.6]

### Teloce integration

- Generated assets revalidate instead of caching stable router/aliases as immutable.
- Client links respect downloads, targets, same-page fragments and unmatched routes.
- Production router optimization uses MinifyJS, alongside Teloce's native production backend.
- Reload watching includes `.vel` sources and ignores `.flaxon` build output.
- Added integration API documentation and five lessons; shortened the README.

### Changed

- Fixed Jinax `CompositeLoader` so custom Admin and module templates can fall
  back to framework package templates such as `admin/base.html`.
- Admin login now redirects authenticated users back to the dashboard instead
  of rendering a second login form after public-site navigation.
- Expanded the school portal example with a responsive institutional website,
  CMS-backed events, admissions, academics, student-life, contact, calendar,
  and public news pages.
- Updated the root README with the current production boundary, optional
  integrations, Admin/CMS capabilities, modules, and microservice guidance.
- Added a zero-to-hero guide matrix and cross-document navigation to the
  documentation landing page and Quick Start.
- Added documentation for the Admin control plane, service-owned databases,
  remote model adapters, service accounts, events, and Flaxon modules.

## [0.2.5] - 2026-09-24

This release consolidates the Admin/CMS, module, router, OpenAPI, and testing
work completed after 0.2.4. It is the current development baseline for the
framework.

### Added

- Admin control plane routes and pages for service registration, health,
  metrics, logs, traces, queues, events, deployments, API keys, audit, storage,
  backups, and status.
- `ServiceRegistry`, `RemoteServiceClient`, and `RemoteModelAdapter` for
  integrating service-owned APIs without direct cross-service database access.
- `AdminDashboard.mount_module()` for custom Admin pages and extensions built
  with `FlaxonModule` and Jinax.
- CMS workspace APIs for calendar, editorial review, publishing, models,
  media, SEO, comments, menus, transfers, and audit data.
- OpenAPI, Swagger UI, ReDoc, Pydantic, FastMCP, GraphQL, and module examples
  with runnable documentation coverage.

### Changed

- Admin control-plane routes are enabled by default. Pass
  `microservices=False` to `AdminDashboard` when an application does not want
  those routes mounted.
- Documentation now distinguishes development defaults from production
  deployments that require persistent storage, Redis, workers, object storage,
  and external delivery services.

## [0.2.4]

A large amount of work landed between 0.1.0 and this release without
intermediate changelog entries being kept up to date. This entry
consolidates that work rather than reconstructing exact per-commit history.

### Added

- Admin dashboard: user accounts, sessions, role-based access control,
  TOTP-based multi-factor authentication with recovery codes, password
  reset, profile management, and CSRF protection on admin forms
- CMS module (`flaxon.admin.cms`): registrable content types with typed
  fields, full CRUD plus bulk actions, taxonomies (categories/tags),
  comments with a moderation queue, revision history with restore,
  scheduled publishing (safe across multiple worker processes via a
  distributed lock), import/export, an extensibility hook system
  (`add_hook`/`run_hook`), and per-content-type WebSocket live-update
  broadcasting
- `flaxon.modules` -- a Flask-blueprint-style `FlaxonModule` composition
  system: route registration, `requires()` dependency validation against
  the DI container at mount time, prefix decided at mount time (not at
  authoring time), module-scoped `before_request`/`after_request` hooks
  and error handlers, nested modules, module-owned CLI commands, and an
  isolated `ModuleTestClient`
- `flaxon.static` -- real static file serving via `app.mount_static()`,
  path-traversal safe and idempotent across repeated mounts
- Router: specificity-based route matching (a literal path segment now
  always wins over a `<param>` pattern, regardless of registration
  order), `include_router(prefix=...)` re-prefixing support, and
  ambiguous-route collision warnings logged at registration time
- `flaxon migrate` wired to a real `MigrationRunner` engine, supporting
  SQLite/PostgreSQL/MySQL via `--database`, plus `--status`, `--target`,
  `--steps`, and `--dry-run`
- `WebSocketManager` now accepts a pluggable `broadcaster`, enabling
  Redis-backed broadcasting across multiple worker processes
- A real browser-based end-to-end test suite (`tests/browser/`) using
  Playwright
- Allowlist HTML sanitizer (`Sanitizer.allow_html`) wired into CMS
  richtext field validation
- Rate limiting on admin/CMS mutation endpoints

### Fixed

- `flaxon generate schema/service/middleware` produced syntactically
  invalid Python (an unsubstituted template placeholder)
- `flaxon shell` crashed immediately on invocation
- `flaxon schedule`/`flaxon worker` did not actually block or run
  correctly; `schedule --once` was accepted but silently ignored
- `Cache.increment`/`Cache.decrement` were unreachable due to incorrect
  indentation placing them outside the `Cache` class
- `MigrationRunner.status()` could report a negative pending-migration
  count in an edge case
- Path traversal in `FileStorage.save()` for Windows-style backslash
  paths (e.g. `..\outside`), previously only caught on POSIX hosts
- Admin dashboard's own index page returned a 500 (template referenced
  an undefined `url_prefix` variable)
- Admin Add/Edit forms silently discarded all submitted fields (`Request`
  had no `.form()` method to parse form-encoded bodies)
- Static admin assets (CSS/JS) 404'd, since nothing served them
- `flaxon_cli.py`-at-project-root CLI plugin discovery silently found
  nothing when run via the installed `flaxon` console script, because the
  current directory wasn't added to `sys.path`
- `doctor --fix` was a no-op; it now generates a real `SECRET_KEY` into
  `.env` when that check fails

### Removed

- Dead code with no callers anywhere in the codebase: a duplicate ASGI
  protocol implementation (`flaxon/asgi/*`, superseded by the real
  implementation in `Flaxon._handle_http`/`_handle_websocket`), a
  duplicate template engine (`flaxon/jinax/{lexer,parser,compiler,...}.py`,
  superseded by the real Jinja2-backed `Jinax` class), and unused
  alternate route-matching implementations
  (`flaxon/routing/{trie,resolver}.py`)

### Changed

- CMS content update requests are now validated per-field against each
  field's declared type before being persisted

## [0.1.0] - 2026-07-22

### Added
- Initial alpha release
- Core framework prototype
- Example applications: hello_api, jinax_site, react_backend, android_backend
- Comprehensive documentation

### Known Limitations (as of 0.1.0, superseded -- see below)
- WebSocket manager is in-memory only (single-process)
- Rate limiter is in-memory only (single-process)
- No OpenAPI generation yet
- No official plugin system yet
- No authentication/authorization modules yet

---

## Known Limitations (current, as of 0.2.4)

- CMS has no reusable media library -- uploads are per-field and are not
  browsable or reusable across multiple content items
- CMS has no built-in public-facing theme/template rendering system; the
  admin panel and JSON API are provided, but rendering a themed public
  site from content is not built in
- CMS `richtext` fields render as a plain textarea in the admin UI --
  there is no WYSIWYG editor, though the backend sanitizer supports safe
  HTML if you author it by hand
- CMS `relationship` and `repeater` field types require hand-written JSON
  in the admin UI -- there is no dedicated picker or list-editor UI yet
- No global, cross-content-type search (search is scoped to one content
  type at a time)
