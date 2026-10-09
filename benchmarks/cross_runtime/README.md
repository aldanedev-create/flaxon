# Flaxon, Node.js, and Go HTTP microbenchmark

This compares Flaxon/Uvicorn with Node's core `http` server and Go's standard
`net/http` server. It does not compare complete full-stack applications or
establish parity with every application written in another language.

Run with Python containing Flaxon, Uvicorn, uvloop, and httptools, plus Node
and a Go toolchain:

```sh
python benchmarks/cross_runtime/run.py --go /path/to/go
```

The runner pins the server and load generator to separate CPU cores, runs one
server at a time with one worker, warms up each endpoint for one second, and
runs three five-second samples in a seeded randomized order. It uses 32
keep-alive connections, one outstanding request per connection, no pipelining.
Every response body and HTTP status is checked. JSON is serialized per request.

Raw results include CPU utilization, request counts, errors, and latency.
The reported p95 is the median of per-run p95 values, not a pooled percentile.
Closed-loop latency can understate overload latency (coordinated omission).
The client shares the host with the server; client CPU approaching 100% means
throughput may be client-limited. Short runs on a shared virtual host are
preliminary measurements, not publishable broad performance claims.

## Developer productivity and defects

HTTP request errors are not developer-induced defects. Neither development
speed nor defect reduction can be inferred from this benchmark or from code
line counts. Both percentages remain **unmeasured**.

A separate study should give developers of mixed experience the same project
specification (authentication, owned projects/tasks, validation, migrations,
Admin, and tests), use idiomatic implementations for each stack, and randomly
assign/counterbalance the stack order. Record active time until the same hidden
acceptance tests pass and independently count reproducible defects against the
same requirements. Include security failures and control for learning effects.
Report participant count, distributions, and confidence intervals.

For a named baseline:

- Time reduction = (baseline time − Flaxon time) / baseline time × 100.
- Development throughput increase = (baseline time / Flaxon time − 1) × 100.
- Defect reduction = (baseline defects − Flaxon defects) / baseline defects × 100.

A zero-defect baseline makes percentage defect reduction undefined. A 50% time
reduction corresponds to a 100% throughput increase; do not confuse them.

## Upgrade comparison

Use `--baseline-source /path/to/unchanged/flaxon/src --output optimized-results.json`
to compare unchanged and modified Flaxon in the same randomized run. FastAPI and
Starlette are included with identical Uvicorn settings. Stateless requests do not
retain cookies; the old Flaxon therefore allocates a session on each request.
This deliberate workload exposes the eager-session behavior. It does not model a
browser that already has a session cookie. Server source changes must be recorded
alongside the framework revision; an unreleased modified tree is not a release.

`profile_request.py` profiles 5,000 direct ASGI requests to expose inspection and
session allocation without socket overhead. cProfile timings are diagnostic and
must not be presented as production request rates.

`serializer_benchmark.py` compares stdlib and orjson separately. Native datetime,
non-finite numbers, very large integers and non-string dictionary keys differ;
Flaxon's default serializer is preserved. Whitespace differences alone do not
represent a JSON semantic incompatibility.

```sh
python benchmarks/cross_runtime/run.py --go /path/to/go --runtimes Flaxon \
  --flaxon-app workload_app:app --paths /session '/validate?n=123' /db \
  --seconds 3 --output workload-results.json
```

These extra workloads measure framework sessions, scalar query validation and
an asynchronous in-memory SQLite count query. The session fixture retains cookies
per connection; the raw client does not enforce browser Secure-cookie behavior.
The SQLite fixture uses a disposable database, not production schema creation.
These are separate diagnostics, not an equivalent full-stack framework comparison.
