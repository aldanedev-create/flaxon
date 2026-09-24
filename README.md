# Flaxon

 
 <p align="center">
  <img src="https://raw.githubusercontent.com/aldanedev-create/Flaxon-Backend-Framework/main/assets/flaxon.png" alt="flaxon Logo"
   width="200"/>
</p>


  
  <p align="center">
  <a href="https://pypi.org/project/flaxon/"><img src="https://img.shields.io/pypi/v/flaxon.svg" alt="PyPI version"></a>
  <a href="https://github.com/aldanedev-create/Flaxon-Backend-Framework/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/code%20style-ruff-000000.svg" alt="Code style: ruff"></a>
</p>

Principal Author: Aldane Hutchinson

Flaxon is an async-first ASGI framework for JSON APIs, WebSockets, and
server-rendered applications. It owns the HTTP boundary while you choose the
database, frontend, queue, and deployment platform.

The project is actively maintained and welcomes contributors. The current
release is suitable for production deployments when configured with persistent
storage, shared infrastructure, workers, and the external services required by
your application. The API may still evolve before 1.0, so pin versions in
production and run the test suite and benchmarks when upgrading.

Flaxon includes an authenticated Admin dashboard, a schema-driven CMS, Jinax
templates, WebSockets, OpenAPI with Swagger UI and ReDoc, GraphQL integration,
database adapters, background work, migrations, and a module system for large
applications. Optional integrations include Pydantic and FastMCP.

Teloce-Py compiles `.vel` single-file components to browser JavaScript and can
be served by Flaxon as a frontend layer. See the Teloce-Py documentation for
the compiler and runtime workflow.

## Install

Flaxon requires Python 3.11 or newer.

```bash
pip install "flaxon[standard]"
```

`standard` installs the recommended ASGI server and template dependencies. For
framework development, install `pip install -e ".[standard,dev]"` instead.

## Your first API

Create `app.py`:

```python
from flaxon import Flaxon

app = Flaxon("hello-api", debug=True)


@app.get("/")
async def home():
    return {"message": "Hello from Flaxon"}


@app.get("/users/<int:user_id>")
async def get_user(user_id: int):
    return {"id": user_id, "name": "Example User"}
```

Start the development server:

```bash
flaxon run app:app --reload
```

Open <http://127.0.0.1:8000/>. For a production process, use `flaxon run`
without `--reload` or run the same ASGI application with Uvicorn.

## Validate JSON input

Use `Schema` parameters for JSON request bodies. Field names use the full
`*Field` spelling.

```python
from flaxon.validation import Schema, fields


class CreateUser(Schema):
    name = fields.StrField(required=True, min_length=2, max_length=80)
    email = fields.EmailField(required=True)
    age = fields.IntField(minimum=13, maximum=120)


@app.post("/users")
async def create_user(data: CreateUser):
    return {"user": data.to_dict()}
```

Available field classes are `StrField`, `IntField`, `FloatField`, `BoolField`,
`EmailField`, `DateField`, `DateTimeField`, `DecimalField`, `UUIDField`,
`ListField`, `ChoiceField`, `NestedField`, and `AnyField`.

## WebSockets

```python
from flaxon.websocket import WebSocket


@app.websocket("/ws/chat/<room_id>")
async def chat(socket: WebSocket, room_id: str):
    await socket.accept()
    await socket.join(room_id)
    try:
        async for message in socket.iter_json():
            await socket.broadcast_json(room_id, {"event": "chat.message", "data": message})
    finally:
        await socket.leave(room_id)
```

The default room manager is in-process. Use shared infrastructure for
cross-worker or multi-instance broadcasts.

## Server-rendered HTML with Jinax

Install the template extra if it is not already included through `standard`:

```bash
pip install "flaxon[templates]"
```

```python
from flaxon.jinax import Jinax

app.use_templates(Jinax("templates", auto_reload=True))


@app.get("/")
async def home(request):
    return await request.render("home.html", {"title": "Welcome"})
```

Jinax uses Jinja2 autoescaping for HTML templates. Only mark content safe when
it has been produced by a trusted sanitizer.

## What Flaxon includes

- HTTP routing, typed path parameters, request parsing, responses, and streams.
- Schema validation and validation decorators.
- Middleware for CORS, request IDs, security headers, trusted hosts, body
  limits, compression, logging, recovery, sessions, and timeouts.
- Sessions, JWT, API keys, authentication, roles, permissions, CSRF, and rate
  limiting.
- WebSocket routes, JSON messaging, rooms, and broadcast helpers.
- Jinax templates, caching helpers, database adapters/transactions,
  background tasks, plugins, OpenAPI, Swagger UI, ReDoc, GraphQL, health
  checks, metrics, and migrations.
- `TestClient` and `AsyncWebSocketClient` for application tests.
- Admin and CMS features for authenticated model management, users, roles,
  media, revisions, publishing, taxonomies, comments, menus, and custom
  Jinax pages.
- `FlaxonModule` composition for mountable application areas, including
  module-owned routes, templates, static files, hooks, and CLI commands.
- An Admin control plane for service registries, remote service model adapters,
  service accounts, operational records, events, and microservice extensions.


## Documentation and examples

- [Documentation home](docs/index.md)
- [Quick start](docs/quickstart.md)
- [Growing a 200-page application](docs/guides/scaling.md)
- [Admin and CMS](docs/guides/admin-cms.md)
- [Microservice control plane](docs/guides/microservices.md)
- [Modules](docs/guides/Modules.md)
- [Deployment](docs/deployment.md)
- [Security](docs/security.md)
- [Examples](docs/examples/)

The runnable example applications live in `docs/examples/`: a basic API,
React backend, Android backend, and Jinax site.

## Production checklist

- Set `DEBUG=False` and a strong `FLAXON_SECRET_KEY`.
- Use explicit allowed origins and trusted hosts.
- Run multiple workers only after moving shared state (sessions, cache, task
  coordination, and WebSocket fan-out) to durable/shared infrastructure.
- Run behind TLS and a reverse proxy or managed load balancer.
- Add database migrations, backups, health checks, metrics, structured logs,
  and load tests for your deployment topology.

See the [deployment guide](docs/deployment.md) for the complete checklist.

## Contributing

```bash
git clone https://github.com/aldanedev-create/Flaxon-Backend-Framework.git
cd Flaxon-Backend-Framework
python -m venv .venv
# Activate the environment, then:
pip install -e ".[standard,dev]"
pytest
```

Flaxon is released under the [MIT License](LICENSE).
