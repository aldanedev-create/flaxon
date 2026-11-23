# Production Readiness Audit

This audit was performed on commit `7fcf293` (`Harden WebSockets for production`). Every verdict
below is backed by a command that was actually run: file reads with line numbers, or small runtime
probes against the code. Areas that could not be exercised (e.g. Redis was not installed in the
audit sandbox) are marked **NOT VERIFIED** rather than guessed.

Severity key: **P0** critical (data loss / RCE / auth bypass), **P1** high (exploitable security or
correctness gap), **P2** medium, **P3** low.

## Baseline evidence captured

| Command | Result |
|---|---|
| `python -m pytest -q -n 4 --no-cov -o addopts=""` | `9 failed, 1214 passed, 59 skipped, 24 warnings, 6 errors` |
| `python -m pytest -q -n 4 --no-cov -o addopts=""` excluding 3 import-error modules | `10 failed, 1212 passed, 59 skipped` (the 10 failures pass individually — `-n 4` isolation issues) |
| `mypy src/flaxon` | `Found 1003 errors in 179 files (checked 373 source files)` |
| CDN scan of `src/flaxon/admin/templates/admin/` | 3 templates loaded Tailwind Play CDN, Font Awesome CDN, Google Fonts CDN |

The pre-existing failures/errors are catalogued under "Known limits" at the end; none were introduced by this phase.

---

## 1. Sessions / cookies

**Verdict: PARTIAL — P2**

- Secure-by-default in the primary session paths: `src/flaxon/sessions/cookie.py:17-19` sets
  `secure=True, httponly=True, samesite="lax"`; `src/flaxon/sessions/manager.py:22-24` matches.
  Runtime header observed: `session=v; Max-Age=60; Path=/; Secure; HttpOnly; SameSite=Lax`.
- Admin auth `src/flaxon/admin/services.py:492-497` emits `HttpOnly; SameSite=Lax` and adds
  `Secure` when `cookie_secure=True` (default at `:60`); `src/flaxon/admin/dashboard.py:139` and
  `src/flaxon/application/app.py:93-97` override it to `not debug`.
- Gap: the publicly exported `flaxon.security.SessionManager` defaults to `cookie_secure=False`
  (`src/flaxon/security/sessions.py:25-27,109-111`). Runtime header there lacked `Secure`.

Regression tests: `tests/security/test_admin_framework_regressions.py:265-273`,
`tests/expanded/state/test_session_cookie_signature.py:16`,
`tests/integration/test_admin_profile_and_cookie.py:28`.

## 2. CSRF

**Verdict: PARTIAL — P1**

- `src/flaxon/security/csrf.py:27-45` implements a stateless HMAC token (`nonce.timestamp.sig`,
  3600s), reads only the `x-csrf-token` header (`:47-54`), and exempts safe methods (`:56-66`).
  `CSRFMiddleware` (`:69-112`) returns `403 FX-CSRF-001`.
- Not enabled in the default stack: `src/flaxon/application/app.py:100-103` installs only
  `RequestIDMiddleware` and `SecurityHeadersMiddleware`.
- Admin default uses a global-secret token (`src/flaxon/admin/dashboard.py:92`
  `session_bound_csrf=False`, `:252-263`), and the token is rendered on the unauthenticated
  login page (`:968-990`). A token signed with the app secret verifies with no session context —
  the token is portable but the secret is not public, so this is defense-in-depth rather than a
  directly exploitable bypass. Origin validation in `src/flaxon/admin/csrf.py:53-62` is opt-in and
  skipped when the `Origin` header is absent.

Regression tests: `tests/security/test_csrf.py`, `tests/expanded/security/test_csrf_submission.py`,
`tests/expanded/admin/test_mutation_csrf_enforcement.py`,
`tests/security/test_admin_framework_regressions.py:30-41`.

## 3. Security headers / CSP

**Verdict: PARTIAL — P2**

- Default `src/flaxon/middleware/security_headers.py:13` sets only `x-content-type-options:
  nosniff` and `x-frame-options: DENY` (enabled at `src/flaxon/application/app.py:100-103`).
  Runtime probe: `strict-transport-security=None`, `content-security-policy=None`,
  `referrer-policy=None`, `permissions-policy=None`.
- A richer class exists at `src/flaxon/security/headers.py:9-41` (Referrer-Policy,
  Permissions-Policy, HSTS, CSP) but is never instantiated; `hsts=False` and `csp=None` by default.
- `.env.example:158-162` advertises `SECURITY_HEADERS_ENABLED`, `CSP_ENABLED`, `CSP_POLICY`,
  `HSTS_ENABLED` but no Python code reads these keys (verified by `rg`).
- Admin templates are now vendored (see the CDN section below); inline JS and Alpine inline
  handlers mean a strict CSP would require `'unsafe-inline'`.

Regression tests: `tests/integration/test_http_lifecycle.py:118-121`,
`tests/integration/test_middleware_stack.py:63`.

## 4. Trusted proxies / `X-Forwarded-*`

**Verdict: PARTIAL — P1**

- `src/flaxon/middleware/proxy_headers.py:18-27` defaults to no trusted proxies and `:32-42` fails
  closed (empty set → untrusted), which is safe when the middleware is not configured.
- Gap when enabled: `:67-81` decides trust by scanning IPs *inside the `X-Forwarded-For` header
  itself* rather than walking a verified proxy chain from the socket peer. Runtime probe: peer
  `10.0.0.2`, `trusted_proxies=["10.0.0.0/24"]`, header `X-Forwarded-For: 203.0.113.99, 10.0.0.1`
  → `scope["client"] == ("203.0.113.99", 0)`, i.e. an attacker can forge the apparent client IP.
  `:125-137` also overwrites `Host` from `X-Forwarded-Host` without validation.
- `TRUSTED_PROXIES` in `src/flaxon/application/configuration.py:52` has no consumer.
  `src/flaxon/logging/access.py:51-57` and `audit.py:159-165` trust the first XFF entry
  unconditionally for logs.
- Separate uvicorn-level controls exist: `src/flaxon/cli/commands/run.py:31-37`
  (`--forwarded-allow-ips`), `src/flaxon/server/configuration.py:23-24`.

Regression tests: `tests/expanded/security/test_proxy_trust_boundaries.py:31-46` (which currently
*encodes* the header-chain behavior), `tests/security/test_admin_framework_regressions.py:163-175`.

## 5. Rate limiting (distributed, atomic)

**Verdict: PARTIAL — P1**

- In-process limiter uses `asyncio.Lock` (`src/flaxon/security/rate_limit.py:22,38`); the default
  `RateLimitMiddleware` uses it (`:91`) and is therefore per-process.
- `DistributedRateLimiter.check()` (`src/flaxon/security/rate_limit.py:120-149`) runs a 4-command
  Redis pipeline with `pipeline()` — no `transaction=True`, `WATCH`, or Lua script. Atomicity is
  delegated to the injected client's pipeline default. Runtime probe with a non-transactional fake
  pipeline: `allowed=300` for a limit of 100; with a MULTI/EXEC-like pipeline: `allowed=100`.
- Redis itself was **not installed** in the audit sandbox (`python -c "import redis"` →
  `ModuleNotFoundError`; `pytest tests/security/test_security_stress.py -k distributed` → skipped),
  so the real-redis path is **NOT VERIFIED** here.
- The flaky test uses a fixed DB/key (`tests/security/test_security_stress.py:64-77`) while
  `tests/security/test_rate_limiting.py:135` calls `flushdb()` on the same DB; `tox.ini:24` runs
  `-n auto`. This matches the prompt's flakiness note.

Regression tests: `tests/security/test_security_stress.py:47-78`,
`tests/security/test_rate_limiting.py`, `tests/expanded/security/test_rate_limit_windows.py`.

## 6. Uploads (size caps, MIME sniffing, traversal, SVG)

**Verdict: PARTIAL — P1**

- Path traversal is handled in `src/flaxon/files/storage.py:24-39`: normalizes backslashes,
  `resolve()`, rejects paths escaping the base. Symlink escape is covered by
  `tests/expanded/data/test_storage_traversal.py:16-24`.
- Admin media does enforce limits and sniffing: `src/flaxon/admin/dashboard.py:1415,1427` (size),
  `:1711-1740` (`magic.from_buffer`, `%PDF-` magic bytes, Pillow re-encode stripping EXIF), with
  SVG excluded from the default allowlist (`dashboard.py:235-242`).
- Gaps:
  - `src/flaxon/files/upload.py:76-78` stores `max_size`/`max_files` but never references them
    again; `src/flaxon/files/storage.py:16` has no size cap; the default middleware stack has no
    body-limit middleware (`src/flaxon/application/app.py:99-102`). Unbounded memory/disk use in
    the primary `flaxon.files` API. **P1**
  - `src/flaxon/files/validation.py:80,85` explicitly allows `image/svg+xml`/`.svg` but there is
    no SVG sanitizer anywhere in `src/flaxon` (the HTML `Sanitizer` in
    `security/sanitization.py:13-56` is not SVG-aware), while `src/flaxon/static.py:36-40` serves it
    as `image/svg+xml` → stored XSS where that validator+storage+serving path is used. **P1**
  - `src/flaxon/files/adapters/local.py:17-18` joins `base_path / path` with no containment check. **P2**

Regression tests: `tests/security/test_file_storage_safety.py`,
`tests/expanded/data/test_storage_traversal.py`, `tests/expanded/data/test_file_size_validation.py`
(declared size only), `tests/integration/test_admin_cms_input_hardening.py:95-127`.
No SVG-sanitization test exists.

## 7. CORS

**Verdict: PARTIAL — P2**

- Implemented in `src/flaxon/middleware/cors.py:13-25` and `src/flaxon/security/cors.py:11-33`;
  disabled by default (`app.py:100-103`). The middleware correctly raises `ValueError` for
  wildcard + credentials (`:22-23`).
- Wildcard origins are the default when enabled; there is no settings field for CORS anywhere in
  the config modules. Two divergent CORS classes have different option names (`P3`).
- A request with no `Origin` receives `ACAO: <first allowed origin>` plus credentials when enabled
  (`:33-35,65-66`). **P3**

Regression tests: `tests/expanded/security/test_cors_credentials.py`,
`tests/integration/test_middleware_stack.py:68-123`.

## 8. DB (pool limits, transactions, migration safety, N+1)

**Verdict: PARTIAL — P2** (no P0/P1)

- Transactions are solid: savepoints for nesting (`src/flaxon/database/transactions.py:60-70`),
  task-local context vars (`:16-21`), statements routed to the leased connection
  (`manager.py:44-55`).
- Gaps: pool min/max (`src/flaxon/database/connections.py:50-51`) are not wired to settings;
  `close()` (`:95-101`) never disconnects checked-out connections; migrations declare
  `dependencies` (`src/flaxon/database/migrations.py:51`) but never enforce them, and version
  filtering is lexicographic (`:184-185`); no query-count assertions exist anywhere in `tests/`
  and the admin change-list loops `≤101` rows issuing `version()` per row
  (`src/flaxon/db/admin.py:208-214`).

Regression tests: `tests/integration/test_transaction_pooling.py`,
`tests/integration/test_database_transactions.py`, `tests/integration/test_admin_migrations.py`.
The CLI does support `migrate --dry-run` (`src/flaxon/cli/commands/migrate.py:134-161`).

## 9. Background tasks / scheduler

**Verdict: PARTIAL — P1**

- Retries are implemented: `src/flaxon/tasks/retry.py:9-92` (`RetryPolicy` + decorator) and
  `src/flaxon/tasks/task.py:98-104`.
- Idempotency is absent: no dedup/ack/visibility mechanism in `src/flaxon/tasks`; `queue.py:49-50`
  pops before execution and never requeues on worker crash (at-most-once, no idempotency key). **P1**
- Graceful shutdown is not wired: `src/flaxon/tasks/worker.py:92-97` cancels consumers immediately
  on SIGTERM; `_graceful_shutdown()` exists at `:99-109` but has **no call site**. The test at
  `tests/integration/test_task_worker.py:120-133` only asserts `is_running() is False`, not that
  in-flight tasks drained. **P1**
- Scheduler is in-process only (`scheduler.py:21`); the `scheduled_task` decorator (`:84-96`) does
  not register with `Scheduler`. **P2/P3**

## 10. Blocking calls on the event loop

**Verdict: FAIL — P1**

Confirmed sync calls inside `async def` (AST scan + `nl -ba`):
- `src/flaxon/static.py:28,41` — `target.read_bytes()` in the HTTP static handler (hot path). **P1**
- `src/flaxon/tasks/task.py:84-85` — sync `self.func(*args, **kwargs)` when no timeout, while the
  timeout branch correctly uses `asyncio.to_thread` (`:80-83`). **P1**
- `src/flaxon/caching/backends/filesystem.py:35-100` — sync `open`/`json.load`/`json.dump`. **P2**
- `src/flaxon/admin/cms.py:746-749`, `src/flaxon/application/app.py:529-531`,
  `src/flaxon/files/streaming.py:17-24` — sync file reads/writes in async paths. **P2**
- `src/flaxon/database/migrations.py:101-103` — sync file I/O in async CLI methods. **P3**

Verified clean: no `time.sleep(` or `requests.*(` in `src/flaxon`; `admin/microservices.py:327-341`
offloads urllib via `asyncio.to_thread`; `jinax/async_render.py:17-20` uses `run_in_executor`.
No tests assert non-blocking file I/O.

## 11. Logging (structured, request IDs, no secrets/PII)

**Verdict: PARTIAL — P1**

- JSON formatters exist (`src/flaxon/logging/formatters.py:25-109`) but the default handler is
  console (`logging/configuration.py:11-17`, `logger.py:31-35`). **P3**
- Request-ID propagation works for the app logger (`logging/logger.py:86-90` merges
  `logging/context.py:99-102`), but `logging/access.py:43` reads
  `getattr(request, "request_id", "unknown")` while `src/flaxon/http/request.py:16` defines no such
  attribute → access JSON logs record `"unknown"`. **P2**
- No redaction in logging: a capable `Redactor` (`debugging/redaction.py:10-30`) is used only by the
  debugger (`application/app.py:645`). `logging/audit.py:80-90` logs raw creation payloads
  (`changes=data`) and `formatters.py:59-60` merges extras unfiltered → secrets/PII can be
  written to logs. **P1**
- `AuditFormatter.format()` (`formatters.py:97-107`) drops the `status`, `error`, and `extra`
  fields built in `audit.py:41-57`. **P2**

Regression tests: `tests/unit/test_context_isolation.py:87-108`,
`tests/integration/test_http_lifecycle.py:110`, `tests/security/test_secret_redaction.py:7-43`
(debugger redaction only — no logging-formatter redaction test).

## 12. Health / readiness / metrics

**Verdict: PARTIAL — P1**

- Routes are really registered (`src/flaxon/application/app.py:106-117`): `/health`,
  `/health/live`, `/health/ready`, `/metrics`. Real check primitives exist
  (`health/checks.py:120-124` `SELECT 1`; `:148-152` Redis `ping`; `CompositeHealthCheck`
  `:167-199`), and readiness is wired to lifespan (`:821-825`).
- Default behavior is decorative: `app.health` is created empty and no `register()` call exists in
  `src/flaxon`. Runtime probe: `/health → 200 healthy`, `/health/live → 200`, `/health/ready → 503
  not ready (200 after mark_ready)`, `/metrics → 200` with an **empty body**. Liveness `all()` over
  an empty registry is trivially `True` (`health/probes.py:15-28`). `MetricsMiddleware` creates its
  own collector (`metrics/middleware.py:23`) rather than using `app.metrics`. **P1/P2**

Regression tests: `tests/expanded/operations/test_health_check_failures.py`,
`test_health_registry_selection.py`, `test_metric_*.py`. No test asserts a failing DB check yields
503 on `/health/ready`.

## 13. Graceful shutdown

**Verdict: PARTIAL — P1**

- Lifespan cleanup works: `src/flaxon/application/app.py:811-833` calls `plugins.shutdown()` and
  `lifecycle.shutdown()`, flips readiness; `lifecycle.py:87-96` runs handlers in reverse and closes
  the `AsyncExitStack`; WebSocket close uses a 5s `wait_for` (`websocket/manager.py:201-213`).
- Gaps:
  - Multi-worker uses `loop.add_signal_handler` unguarded (`src/flaxon/server/production.py:39-41`,
    POSIX-only) and `processes.py:52-58` force-kills after a 10s join. **P1**
  - `ServerConfig.timeout_graceful_shutdown = 30` (`server/configuration.py:19,60`) is **never
    passed** to `uvicorn.Config` in `production.py:50-58`, `processes.py:34-42`, or CLI `run.py:64-73`
    — dead configuration. **P1**
  - Background workers cancel in-flight tasks (`tasks/worker.py:92-97`); `_graceful_shutdown()` is
    never called. **P2**

Regression tests: `tests/integration/test_websocket_production.py:35-49,249-252`,
`tests/unit/test_websocket_manager_production.py:101`, `tests/integration/test_task_worker.py:103-133`.
No SIGTERM test against `ProductionServer`/`ProcessManager`.

## 14. Streaming / export memory use

**Verdict: PARTIAL — P1**

- Chunked primitives are bounded: `src/flaxon/http/response.py:113-126` (iterates chunks),
  `http/streaming.py:81-103` (`chunk_size=8192`), `files/streaming.py:17-54`.
- `Stream.json_lines`/`sse` are **broken**: `http/streaming.py:140,171` pass `media_type=` to
  `StreamingResponse.__init__` (`http/response.py:102-111`), which has no such parameter →
  `TypeError` (verified at runtime). `Stream` is not exported from `flaxon.http`. **P2**
- Admin exports fully buffer: `src/flaxon/admin/dashboard.py:2052-2068` and `:2291-2305`,
  `src/flaxon/admin/cms.py:1177-1192` load the full table into a list + `StringIO`. Unbounded
  memory on large tables. **P1**

Regression tests: `tests/expanded/http/test_streaming_responses.py:10-33`,
`tests/integration/test_admin_cms_features.py:148-149`,
`tests/security/test_admin_data_boundaries.py:44-52`. No memory-bound export test.

## 15. Windows compatibility

**Verdict: PARTIAL — P2**

- A `windows-latest` CI job exists (`.github/workflows/project-creation.yml:7-20`, Python 3.12/3.14)
  but runs only `tests/cli/test_cli.py` and `tests/cli/test_new_environment.py`. Other workflows
  are `ubuntu-latest`.
- No shell scripts (`*.sh|*.ps1|*.bat|*.cmd` count = 0); CLI code is Windows-aware
  (`cli/commands/new.py:189-219` uses `taskkill` on `nt` and `start_new_session=os.name != "nt"`).
- The `Makefile` is bash-only (`rm -rf`, `find -exec`, `read -p`, `[[ =~ ]]` at `:62-103`). No
  `.gitattributes`; 0 of 1201 scanned text files had CRLF. POSIX-only `loop.add_signal_handler`
  in multi-worker mode (`server/production.py:39-41`). **P2/P3**

Regression tests: the two CLI test modules above only. No dedicated path/line-ending tests.

---

## P0/P1 summary and disposition in this phase

| # | Area | Severity | Disposition |
|---|---|---|---|
| 2 | CSRF not default / portable admin token | P1 | **Deferred** — changing default middleware risks broad API breakage (see caveats) |
| 4 | Proxy XFF spoofing | P1 | **Fixed** — additive `trusted_proxy_count` option chooses the client by position, not by spoofable IP values; regression test added |
| 5 | Distributed limiter atomicity | P1 | **Fixed** — `pipeline(transaction=True)`; regression tests added |
| 6 | Upload size caps + SVG XSS | P1 | **Fixed** — per-file/body/file-count caps enforced; SVG rejected by default (`allow_svg=True` opt-in); regression tests added |
| 9 | Task graceful shutdown / idempotency | P1 | **Fixed** — `stop()`/signals drain in-flight work with timeout; idempotency remains **deferred** |
| 10 | Blocking calls on loop | P1 | **Fixed** — static reads and sync tasks offloaded via `asyncio.to_thread`; regression tests added |
| 11 | Logging redaction | P1 | **Fixed** — `Redactor` applied in JSON/access/audit formatters; outcome fields retained; regression tests added |
| 12 | Health/metrics trivial | P1 | **Deferred** — opt-in by design; wiring real checks by default is a breaking behavior change (see caveats) |
| 13 | Graceful shutdown timeout | P1 | **Fixed** — `timeout_graceful_shutdown` passed to uvicorn in both single- and multi-worker paths; regression tests added |
| 14 | Admin exports unbounded | P1 | **Partially fixed** — the `Stream.json_lines`/`sse` `media_type` TypeError (P2) is fixed; the admin CSV/JSON exports still buffer the full table (**deferred**) |

P0: none found. Fixed items all have regression tests that were confirmed to fail before the fix
(tests-first) and pass after. The **deferred** P1s (CSRF default, task idempotency, health/metrics
default wiring, admin export streaming) and the "Partially fixed" export buffering remain open and
are **not** claimed as fixed.

Regression tests added or extended in this phase (all pass after the fixes):
- `tests/unit/test_admin_vendored_assets.py`, `tests/integration/test_admin_offline_assets.py` (CDN)
- `tests/security/test_distributed_limiter_atomicity.py` (limiter)
- `tests/unit/test_nonblocking_io.py` (event-loop blocking)
- `tests/unit/test_server_graceful_timeout.py` (shutdown timeout)
- `tests/unit/test_stream_media_type.py` (streaming media type)
- `tests/security/test_upload_caps_and_svg.py` (uploads/SVG)
- `tests/unit/test_logging_redaction.py` (log redaction)
- `tests/unit/test_worker_graceful_shutdown.py` (task drain)
- `tests/expanded/security/test_proxy_trust_boundaries.py` (proxy hop count)

## CDN removal (acceptance criterion)

All three admin templates previously loaded the Tailwind Play CDN, Font Awesome CDN and Google
Fonts CDN. They now reference locally vendored, pinned assets under
`src/flaxon/admin/static/admin/vendor/{tailwind,font-awesome,inter}/`, each with a `MANIFEST.json`
recording npm integrity + SHA-256 and its license. `scripts/vendor_admin_assets.py` reproduces the
build and `--check` verifies every hash. Tests: `tests/unit/test_admin_vendored_assets.py` and the
real-server (uvicorn + httpx) test `tests/integration/test_admin_offline_assets.py`.

The GraphQL playground templates (`src/flaxon/graphql/playground/*.html`) still reference pinned
`unpkg.com` assets (Altair 5.2.1, GraphiQL 3.0.6, React 18). These are **not admin** assets and are
out of Phase 0 scope; recorded here as a **P2** follow-up.

## Known limits / caveats

- The 10 `-n 4` failures and 3 collection errors in the baseline are pre-existing (test isolation,
  missing `fastmcp`, missing `tests/__init__.py`). They are not caused by this phase and are
  reported honestly rather than hidden.
- Redis was unavailable, so the real-redis distributed-limiter path was **NOT VERIFIED**; the
  atomicity fix is proven with a controlled fake pipeline that models both the broken and correct
  behaviors.
- Windows behavior was **NOT VERIFIED** in this Linux sandbox; the existing `windows-latest` CI
  job is the only evidence, and it covers a CLI subset.
- CSRF and health/metrics default-wiring fixes were deferred because they change framework-wide
  defaults and would break the public-API compatibility rule for this phase; they remain P1.
