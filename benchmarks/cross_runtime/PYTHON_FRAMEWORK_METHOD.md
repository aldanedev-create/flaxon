# Six-framework ASGI comparison

This suite evaluates Flaxon, FastAPI, Starlette, Litestar, Sanic and Falcon.
It tests a hypothesis; it does not assume Flaxon wins.

## Workloads

Every app registers the same three fixed endpoints and 1,000 dynamic routes.
The dynamic request targets the last registered route. Each framework uses its
normal JSON response API, with serialization performed for every request.

- `/plaintext`: thirteen-byte plaintext response.
- `/json`: a single-field JSON object.
- `/large-json`: 1,000 task objects with identical values.
- `/routes/999/42`: typed dynamic route, returning the identifier and route index.

These apps intentionally have no database, authentication, sessions in use,
application middleware, or templates. Large route sets help reveal routing
cost that a two-route hello-world comparison misses. They are not equivalent
to a complete production application.

## Controls

One Uvicorn worker per app, uvloop, httptools, access logging disabled. Server
and client pinned to separate CPUs; 32 keepalive connections with one request
outstanding per connection. Three randomized three-second samples per
framework/workload, each preceded by a one-second warmup. All frameworks run
on the same shared Linux host. Record exact versions and source checksums.

The client handles Content-Length and chunked transfer encoding, parses JSON,
and verifies every field and row. Any response or connection error invalidates
the run rather than contributing to a speed ranking. Latency starts when a
request is sent; this closed-loop test does not measure overload behavior.

Sanic is measured in ASGI mode to keep the server controlled; these numbers do
not rank Sanic's native server. Falcon is its ASGI implementation. Neither
framework is given pre-encoded JSON or response caching. Framework defaults
can still differ in included functionality and serialization behavior.

CPU counters include startup and warmup, so use them only diagnostically.
Large-response JSON verification may saturate the client CPU: such samples
cannot establish the server's maximum throughput. Report all sample ranges,
not only an aggregate score.

## Reproduce

```bash
pip install -e '.[standard]'
pip install -r benchmarks/cross_runtime/requirements-frameworks.txt
python benchmarks/cross_runtime/run.py \
  --go /path/to/go \
  --runtimes Flaxon,FastAPI,Starlette,Litestar,Sanic,Falcon \
  --flaxon-app framework_apps:flaxon_app \
  --paths /plaintext /json /large-json /routes/999/42 \
  --seconds 3 --repeats 3 --output python-framework-results.json
```

The existing runner records Node/Go versions and builds the Go reference binary,
even when selecting Python-only runtimes; Node is the shared load generator.

## Claims this can support

A supported statement names the tested frameworks, workload, versions, server,
and machine. A single shared-host run cannot establish a global ranking among
all Python frameworks. Extend with longer samples, independent hardware,
concurrency sweeps, database and validation workloads, and native-server tests
before using a broad marketing superlative.

Official API references used for the adapters:

- https://docs.litestar.dev/main/usage/routing/handlers.html
- https://sanic.dev/en/guide/running/running.md
- https://falcon.readthedocs.io/en/stable/user/quickstart.html
