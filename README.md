<div align="center">
  <a href="https://flaxon-website.vercel.app/">
    <img src="https://raw.githubusercontent.com/aldanedev-create/flaxon/main/assets/flaxon.png" alt="Flaxon logo" width="200">
  </a>

  <h1>Flaxon</h1>

  <p><strong>The Python full-stack framework.</strong></p>
  <p>Simple Python. Serious Applications.</p>

  <a href="https://pypi.org/project/flaxon/"><img src="https://img.shields.io/pypi/v/flaxon.svg?style=for-the-badge" alt="PyPI version"></a>
  <a href="https://pypi.org/project/flaxon/"><img src="https://img.shields.io/pypi/pyversions/flaxon?style=for-the-badge" alt="Supported Python versions"></a>
  <a href="https://github.com/aldanedev-create/flaxon/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="MIT License"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/code%20style-ruff-000000.svg?style=for-the-badge" alt="Code style: Ruff"></a>

  <p>
    <a href="https://flaxon-website.vercel.app/docs.html">Documentation</a> ·
    <a href="docs/getting-started.md">Getting Started</a> ·
    <a href="examples/">Examples</a> ·
    <a href="CONTRIBUTING.md">Contributing</a>
  </p>
</div>

## Getting Started

Flaxon is an async-first Python full-stack framework for building web applications with an integrated frontend, backend, authenticated Admin dashboard, and development tools. Build interactive interfaces with **Teloce**, render HTML on the server with **Jinax**, or combine both in one application.

Flaxon brings together HTTP routing, JSON APIs, validation, authentication, WebSockets, database adapters, migrations, background work, a schema-driven CMS, and mountable application modules. You choose the database, queue, and deployment platform that fit your application.

Requires **Python 3.11 or newer**.

```bash
python -m pip install "flaxon[standard]"
flaxon new my-project
cd my-project
```

Activate the generated virtual environment:

```bash
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the application and start development:

```bash
python -m pip install -e .
python management.py migrate
python management.py setup-admin
flaxon run app:app --reload
```

Open [localhost:8000](http://127.0.0.1:8000/) for the welcome application, [/server-page](http://127.0.0.1:8000/server-page) for the Jinax example, and [/admin/login](http://127.0.0.1:8000/admin/login) for Admin. Admin setup prompts for your own credentials.

The default starter includes:

- A modular application with `FlaxonModule` and `app.mount_module()`.
- A Teloce interface with scoped CSS and a TypeScript API helper.
- A complete Jinax server-rendered page.
- Persistent SQLite application and Admin storage.
- `management.py` for migrations, Admin setup, and superuser creation.
- Module-owned custom commands: try `flaxon welcome` and `flaxon welcome-status`.

Use `flaxon new my-api --template basic` for a smaller starter. The CLI also works through `python -m flaxon`.

These instructions describe the current repository starter. See the [installation guide](docs/installation.md) for package and environment setup.

## Your Interface, Your Choice

**Flaxon + Teloce** gives you an interactive full-stack application. Teloce-Py compiles components and TypeScript into browser JavaScript; Flaxon serves the application and its APIs. MinifyJS optimizes production JavaScript. Modules can own both backend endpoints and frontend pages.

**Flaxon + Jinax** gives you a complete server-rendered application using Jinja2-based HTML templates. You can build your entire application this way, including routes, forms, authentication, database operations, and Admin.

You can also use Flaxon as the backend for another frontend or mobile client.

Read the [Teloce integration guide](docs/api/teloce.md), [Jinax guide](docs/guides/jinax.md), and [module guide](docs/guides/Modules.md).

## Your First API

For a standalone API, create `app.py`:

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

Run it with:

```bash
flaxon run app:app --reload
```

Add validated JSON input with Flaxon's schema fields:

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

See [routing](docs/guides/routing.md) and [validation](docs/guides/validation.md) for more examples.

## Built-in Features

- **Application foundation:** ASGI, async routing, typed path parameters, request parsing, responses, and streams.
- **Frontend and templates:** integrated Teloce interfaces, Jinax templates, scoped component styles, and production JavaScript optimization.
- **Admin and CMS:** authenticated model management, users, roles, media, revisions, publishing, taxonomies, comments, menus, and custom Jinax pages.
- **Security and middleware:** sessions, JWT, API keys, roles, permissions, CSRF, rate limiting, CORS, security headers, trusted hosts, request IDs, body limits, compression, logging, recovery, and timeouts.
- **Real-time applications:** WebSocket endpoints, JSON messaging, rooms, and broadcast helpers.
- **Data and background work:** database adapters, transactions, migrations, caching helpers, and background tasks.
- **API tooling:** OpenAPI, Swagger UI, ReDoc, GraphQL integration, and optional Pydantic and FastMCP integrations.
- **Modular applications:** module-owned routes, templates, static files, frontend sources, lifecycle hooks, and CLI commands.
- **Testing and operations:** `TestClient`, `AsyncWebSocketClient`, health checks, metrics, and an Admin control plane for service registries, remote model adapters, service accounts, operational records, and events.

Some integrations require optional dependencies. See [installation](docs/installation.md) and the relevant feature guide.

## Documentation

Visit the [Flaxon documentation website](https://flaxon-website.vercel.app/docs.html) or browse the [documentation in this repository](docs/index.md).

- [Getting started](docs/getting-started.md)
- [Admin and CMS](docs/guides/admin-cms.md)
- [Modules and application composition](docs/guides/Modules.md)
- [Growing a 200-page application](docs/guides/scaling.md)
- [WebSockets](docs/guides/websockets.md)
- [Databases](docs/guides/databases.md)
- [Microservice control plane](docs/guides/microservices.md)
- [Testing](docs/guides/testing.md)
- [Deployment](docs/deployment.md)

Explore the [example applications](examples/) and [backend examples](docs/examples/), including the [modular Teloce shop](examples/teloce_modules_shop/), [Teloce taskboard](examples/teloce_taskboard/), and [school portal](examples/school_portal/).

## Deployment

Flaxon applications run as ASGI applications through `flaxon run` or an ASGI server such as Uvicorn. Configure debug mode, secrets, allowed origins, and trusted hosts for your environment.

Use durable storage and shared infrastructure where your worker topology requires it. The default WebSocket room manager is in-process; cross-worker broadcasts need shared infrastructure. The generated Admin store is a single-node starter configuration.

Follow the [deployment guide](docs/deployment.md) and [Admin production guide](docs/guides/admin-production.md) for workers, TLS, migrations, backups, health checks, and monitoring. Pin dependency versions and test upgrades.

## Community and Contributing

Flaxon is created and maintained by **Aldane Hutchinson**. Bug reports, documentation improvements, examples, and code contributions are welcome.

Use [GitHub Issues](https://github.com/aldanedev-create/flaxon/issues) to report reproducible bugs or suggest features. Read the [contribution guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

For local framework development:

```bash
git clone https://github.com/aldanedev-create/flaxon.git
cd flaxon
python -m venv .venv
# Activate the environment, then:
python -m pip install -e ".[standard,dev]"
pytest
```

## Security

Report vulnerabilities privately using the instructions in [SECURITY.md](SECURITY.md).

## License

Flaxon is released under the [MIT License](LICENSE).
