# Verified Flaxon pitfalls (0.3.2)

Generated from `scripts/generate_ai_docs.py`; every row is checked
against live code by `tests/docs/test_ai_docs.py`. Do not edit by hand.

| Topic | Do | Don't |
| --- | --- | --- |
| Route parameters | Use `<int:id>` for typed path parameters. | Do not use `{id}` or `{id:int}`; they never match a request. |
| OpenAPI docs | Pass `Flaxon('x', openapi=True)` to serve `/docs`. | A plain `Flaxon('x')` has no `/docs` route. |
| WebSocket extras | Install `flaxon[standard]` (uvicorn + websockets) to serve sockets. | Plain `uvicorn` without `websockets` returns 404 for every socket. |
| Validation errors | Expect HTTP 422 with `error.code == 'FX-VAL-001'` and an `error.fields` map. | Do not assume a flat error body or a 400 status. |
| Test clients | Use `TestClient.get(path, query={...})` / `TestClient.post(path, json_data={...})`. | Do not pass a `json=` keyword; use `json_data=`. |
| Project templates | Use `flaxon new NAME --template` with `basic`, `api`, `api-db`, `web` or `fullstack`. | Do not invent template names; the CLI validates choices. |
| Admin registration | Use a `Resource` subclass with `model` and `fields`, then `dashboard.register(MyResource)`. | Legacy `register(model, list_display=[...])` still works but is additive-only; do not mix field APIs. |
| WebSocket close codes | Reject bad origins before accept; clients see HTTP 403 / close code 1008. | Do not rely on browser same-origin policy for WebSockets; check `Origin` explicitly. |
