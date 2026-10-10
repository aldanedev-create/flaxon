# Routing and quality audit

This audit starts from commit `f4ab3cd440234750f6220ee2fc107dde58b93132`.
It improves HTTP route lookup and error visibility, fixes the whole-package
mypy invocation, and adds gates against new lint debt. The historical measurements below precede the complete lint cleanup documented
at the end. Flaxon is not fully type-checked.

## HTTP routing

Dynamic routes are indexed by their literal path segments before the first
parameter. `/api/projects/<int:project_id>` no longer needs to check unrelated
`/api/tasks/...` routes. The index stops before a mixed segment or parameter:
custom converters and `<path:...>` may match slashes, so their regex remains
the authority. Candidate lists retain specificity and registration order;
specificity is calculated once rather than repeatedly during matching.

Exact static routes keep the dictionary lookup. A static route for a different
HTTP method still allows a matching dynamic route to handle the request.
Typed conversion, 404/405 handling, mounting, and late registration are covered
by regression tests against an ordered reference matcher. Registration updates
the index immediately; it does not cache request values or dependency instances.

Routes with an early parameter can still share a broad candidate list. This is
not a complete segment trie for every converter, and WebSocket matching is
unchanged. Treat registered route definitions as immutable; add routes through
`Router` decorators and `include_router()`.

### Route-only measurements

Measured in the same Linux container with Python 3.12.14 on AMD EPYC 9V74.
Each resource has one static route and one dynamic route under `/api`.
Each value is the median of seven samples, each containing 3,000 verified
lookups. Paths and IDs vary during the dynamic run. Before uses the base commit;
after uses this implementation. Values are microseconds per lookup.

| Resource pairs | Dynamic before | Dynamic after | 404 before | 404 after | 405 before | 405 after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 7.63 | 1.82 | 7.93 | 1.76 | 8.82 | 2.44 |
| 100 | 27.30 | 1.91 | 33.15 | 1.71 | 36.14 | 2.61 |
| 1,000 | 245.95 | 2.20 | 298.53 | 1.89 | 296.62 | 2.73 |

Static hits measured approximately 0.37–0.47 microseconds in both versions.
The large dynamic improvement applies to this common-prefix workload. It does
not measure HTTP throughput, middleware, database queries, or application work,
and it does not establish a ranking against other frameworks. Shared-container
load and path shape affect the numbers.

Run from an installed checkout:

```bash
python benchmarks/router_scaling.py
python -m cProfile -s cumulative benchmarks/router_scaling.py --iterations 1000
```

## Exception boundaries

Counting only unnamed `except Exception:` misses most broad handlers. The base
has 94 broad handlers (30 unnamed), plus one `suppress(Exception)`. This change
has 88 broad handlers (26 unnamed) and no `suppress(Exception)`.

The important changes are behavior, not the count:

- Task signal listeners log failures with tracebacks and continue to other
  listeners. Cancellation propagates. Listener subscriptions are snapshotted
  for each emission so disconnecting during dispatch cannot skip another listener.
- Worker queue failures log and retry with exponential delays from 0.1 seconds
  to a maximum of five seconds. Successful queue reads reset the delay. This
  prevents an unavailable backend from causing a busy loop.
- S3 `exists()` returns `False` only for a missing object. Access-denied,
  connection, service, and unexpected errors propagate instead of masquerading
  as missing files. Applications relying on the previous fallback must handle
  those backend errors explicitly.
- Annotation resolution catches expected unresolved-annotation errors.
  Compression decoding translates known gzip/deflate errors into `BadRequest`
  while unexpected programming errors propagate.
- Persisted queries tolerate invalid JSON and malformed extension shapes;
  unexpected request-reader errors propagate. WebSocket token decoding catches
  known malformed-value errors rather than every exception.

Retained broad catches serve different contracts: user callback/plugin/CLI
boundaries record failures, application recovery translates unexpected errors
into server responses, cleanup handlers rethrow after releasing resources,
database health probes report unavailability, debug inspection protects the
original error from failing `repr`/inspection, and validation or disconnected
WebSocket handling fails closed. These should be reviewed by their contract;
mechanically replacing them with `suppress(Exception)` hides the same problem.
This audit is not an independent security assessment of every subsystem.

Inventory named catches, unnamed catches, and suppressions together:

```bash
python scripts/audit_exceptions.py
```

## Typing

`mypy_path` now points to the repository's `src` directory. The whole-package
command no longer stops because `src.flaxon.exceptions` and `flaxon.exceptions`
are discovered as different modules.

```bash
python scripts/typecheck.py        # Required core gate
python scripts/typecheck.py --full # Report wider debt; currently fails
```

The strict core gate grew from three to 11 modules: route preparation,
converters, parameters, definitions and matching, dependency resolution, task
signals/workers, body decoding, JSON serialization, and JWT. The gate does not
follow imports into unchecked modules; passing it is not a whole-package typing
claim. The full command reported 881 errors across 172 files in the validation
environment. Optional dependencies can affect that report. No global
`ignore_errors` or `ignore_missing_imports` was added to mask this debt.

`mypy.ini`, `ruff.toml`, and `tox.ini` are the authoritative configurations;
competing configurations were removed from `pyproject.toml`.

## Lint debt

Using Ruff 0.16.10, findings dropped from 3,871 to 3,442 through safe import,
docstring-format, newline and stale-suppression fixes, targeted API documentation,
and formatting of smaller affected modules. No rules were disabled to obtain
that reduction. Public docstrings, embedded long lines, and complex functions
still account for substantial debt.

```bash
python scripts/check_lint_budget.py # Reject increases by file and rule
ruff check src/flaxon             # Show every remaining finding
```

CI uses the pinned Ruff version and `scripts/lint-baseline.json`. New files have
no allowance. Fix new findings; never increase the baseline to accept them.
When reducing existing debt, lower the corresponding allowances in the same PR.
The budget does not turn existing warnings into clean code, and per-file counts
cannot identify a replacement warning when another warning of the same rule was
removed. Review changed code and continue reducing the baseline.

## Verification and remaining coverage gap

The full suite with benchmark timing disabled completed with **933 passed and
32 skipped**. The unchanged base completed with **905 passed and 32 skipped**
in the same environment. Real browser and externally configured integrations
require their separate test environments.

Both coverage-enabled commands exited unsuccessfully because the configured
80% threshold is not reached: **46.41% before, 47.11% after**. The threshold was
not lowered. Test assertions passing does not mean the coverage gate passed.
The expanded request/security CI command, which intentionally runs without
coverage options, passed **279 tests, with two skipped**. All four benchmark
fixture tests also passed with benchmark measurements enabled.

```bash
pytest tests --benchmark-disable
# Runs all assertions and reports the existing coverage-threshold failure.
```

## Follow-up lint cleanup

A second pass reduced Ruff 0.16.10 findings from **3,442 to 2,973** (469
removed). It adds 388 public API docstrings across caching, dependency injection,
tasks, and logging, plus reviewed import and formatting cleanup. Parent-relative
imports now use equivalent absolute Flaxon paths. Optional integrations retain
their lazy imports. No lint rules were disabled, and every file/rule allowance
was reduced or kept unchanged.

The pass also fixes shared mutable context defaults and cached context
dictionaries. Request and logging helpers read the active context dynamically;
context mutations copy their dictionaries so child tasks cannot overwrite their
parent's values. Task and dependency contexts use immutable defaults. Logging
configurations copy handler definitions, and rotating file handlers now pass
size, backup count, and encoding by name to the standard library handler.

Thirteen regression tests cover independent contexts, concurrent tasks and
logging middleware, nested context restoration, configuration isolation, and
actual log rollover. These tests are included in the request/security CI job.
The strict typing gate now checks **15 modules**, adding the four context
modules. This remains targeted coverage rather than a whole-package typing
claim.

The full suite completed with **946 passed and 32 skipped**, with default
coverage options and benchmark timing disabled. This verifies test assertions;
the existing coverage gap described above remains.


## Complete configured lint cleanup

The remaining 2,973 active findings are resolved. Ruff 0.16.10 now passes
`ruff check src/flaxon`, and the per-file baseline is empty. CI runs every
configured rule. No rule selection or global/per-file ignore was broadened.
This means clean under the repository's existing configuration, not every
possible Ruff rule or a complete security/type audit.

The changes document public APIs, simplify large handlers, validate SQL
identifiers, preserve lazy optional imports, and fix synchronous cache writes.
Admin/CMS authorization, CSRF checks, transaction boundaries, stale-edit checks,
and route registration order remain part of regression testing.

Reviewed local exceptions retain established positional public APIs and the
standard-library redirect-handler signature (PLR0917). CLI subprocess calls
use argument lists without a shell (S603); outbound service requests validate
HTTP(S) URLs and disable redirects (S310). The explicit trusted pickle mode
retains S301 with a warning at the call site. These exceptions are visible
`noqa` annotations with reasons, not globally disabled rules. Therefore this
is not a claim that every former finding was fixed without suppressions.

Task pickle loading now rejects arbitrary imported globals by default. Ordinary
containers and allowlisted datetime, decimal and UUID values still round-trip.
Custom classes need `Serializer.from_pickle(data, trusted=True)`, which can
execute code and must never receive user-controlled or unauthenticated input.
The restricted loader does not prevent memory-exhaustion or other resource attacks;
prefer JSON for external inputs. Existing exception imports retain aliases to
Error-suffixed classes; code relying on an exception's `__name__` should migrate.

The strict typing gate remains limited to 15 core modules. The existing overall
coverage threshold and optional browser/service test requirements are unchanged.
