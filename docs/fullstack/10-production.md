# Lesson 10: Build, deploy and maintain the complete application

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


## Choose the remaining framework capabilities deliberately

A production full-stack app can add these features without replacing its UI:

- **OpenAPI:** document API contracts and expose interactive API documentation.
- **GraphQL:** provide a separate data-query interface where it fits the client.
- **Admin/CMS:** manage application content and operations with its authorization.
- **Tasks:** move expensive work to workers, with retries and scheduling.
- **Plugins/FastMCP/ASGI mounts:** integrate distinct services through supported lifecycles.
- **Health, metrics and logs:** observe readiness and failures without publishing secrets.

Use the [course coverage map](index.md#complete-reference-coverage) to reach the
actual configuration APIs. These are opt-in application choices, not features
automatically activated by `use_teloce()`.

For Teloce, review compiler options, shared runtime selection, scoped CSS,
asset hashing, source maps and MinifyJS bundling. Verify output with actual pages
and lazy imports before enabling a new optimization. Teloce plugins/tooling and
standalone runtime features have their own documented scope; they are not
interchangeable with Flaxon server plugins.

## Repeatable checks

```bash
python -m pytest -o addopts='' tests/integration/test_teloce_integration.py
```

The integration suite builds both examples, checks generated assets and validates
API behavior. GitHub Actions also launches Chromium for UI interactions. For your
own production application, add authorization, persistence and worker tests;
the course fixtures do not cover your business rules.


[Course contents](index.md) · [Previous lesson](09-live-updates.md)
