# Quick Start

Build and run a small Flaxon application in a few minutes. This page is the
shortest path from installation to a working HTTP API. Use the navigation
links below to continue into the larger developer guides.

**Developer navigation:** [Documentation home](index.md) | [Installation](installation.md) | [Routing](guides/routing.md) | [Requests](guides/requests.md) | [Responses](guides/responses.md) | [Validation](guides/validation.md) | [Jinax templates](guides/jinax.md) | [WebSockets](guides/websockets.md) | [Testing](guides/testing.md)

## 1. Create a project

Create a directory and a virtual environment:

=== "Linux and macOS"

    ```bash
    mkdir my-flaxon-app
    cd my-flaxon-app
    python3 -m venv .venv
    source .venv/bin/activate
    ```

=== "Windows PowerShell"

    ```powershell
    mkdir my-flaxon-app
    cd my-flaxon-app
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```

Flaxon supports Python 3.11 and newer. Install the framework with the
development server and template dependencies:

```bash
python -m pip install "flaxon[standard]"
```

## 2. Create the application

Create `app.py` and paste this complete example:

```python
from flaxon import Flaxon
from flaxon.validation import Schema, fields


app = Flaxon("hello-world", debug=True)


class CreateUser(Schema):
    name = fields.StrField(required=True, min_length=2, max_length=80)
    email = fields.EmailField(required=True)


@app.get("/")
async def home():
    return {"message": "Hello from Flaxon"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "hello-world"}


@app.get("/users/<int:user_id>")
async def get_user(user_id: int):
    return {"id": user_id, "name": f"User {user_id}"}


@app.post("/users")
async def create_user(data: CreateUser):
    return {"success": True, "user": data.to_dict()}
```

The application object must be named `app` when you run `app:app`. You can
choose another module or variable name, but the CLI target must always use the
form `module:object`.

## 3. Run the development server

Run this command from the project directory:

```bash
flaxon run app:app --reload
```

Open these URLs:

| URL | Purpose |
| --- | --- |
| `http://127.0.0.1:8000/` | Application response |
| `http://127.0.0.1:8000/health` | Health response |
| `http://127.0.0.1:8000/users/42` | Typed route parameter |

Test the validated endpoint with `curl`:

```bash
curl -X POST http://127.0.0.1:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Ada Lovelace","email":"ada@example.com"}'
```

Flaxon returns a validation error response when a required field, email
address, length limit, or other schema rule is invalid. See the
[Validation guide](guides/validation.md) for nested schemas and custom rules.

## 4. Add HTML with Jinax

Install the template extra:

```bash
python -m pip install "flaxon[templates]"
```

Create `templates/home.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
  </head>
  <body>
    <h1>{{ title }}</h1>
    <p>{{ message }}</p>
  </body>
</html>
```

Register Jinax in `app.py` and add a rendered route:

```python
from pathlib import Path

from flaxon.jinax import Jinax


app.use_templates(Jinax(Path(__file__).parent / "templates"))


@app.get("/welcome")
async def welcome(request):
    return await request.render(
        "home.html",
        {"title": "Welcome", "message": "Your Jinax page is running."},
    )
```

For template inheritance, autoescaping, forms, and custom filters, continue to
the [Jinax guide](guides/jinax.md).

## 5. Add a WebSocket

WebSocket routes are asynchronous and can send JSON messages:

```python
from flaxon import WebSocket


@app.websocket("/ws/echo")
async def echo(socket: WebSocket):
    await socket.accept()
    async for message in socket.iter_json():
        await socket.send_json({"echo": message})
```

Use the [WebSockets guide](guides/websockets.md) for rooms, broadcasts,
authentication, heartbeats, and production deployment.

## 6. Choose the next guide

| You want to build | Continue with |
| --- | --- |
| A structured API | [Routing](guides/routing.md), [Requests](guides/requests.md), [Responses](guides/responses.md), and [Validation](guides/validation.md) |
| A server-rendered site | [Jinax](guides/jinax.md) and [Jinax API reference](api/jinax.md) |
| Login and permissions | [Authentication](guides/authentication.md) and [Authorization](guides/authorization.md) |
| Admin and CMS workflows | [Admin and CMS](guides/admin-cms.md), [Admin production](guides/admin-production.md), and [Admin guide](admin-guide.md) |
| Database-backed content | [Databases](guides/databases.md) and [Migration guide](migration-guide.md) |
| Background work | [Tasks](guides/tasks.md) and [Scaling](guides/scaling.md) |
| Tests and diagnostics | [Testing](guides/testing.md) and [Debugging](guides/debugging.md) |
| Production deployment | [Deployment](deployment.md), [Security](security.md), and [Performance](performance.md) |
| Mobile or frontend clients | [Mobile backends](guides/mobile-developement.md) and [Frontend integration](examples/frontend-integration.md) |

**More developer navigation:** [API reference](api/application.md) | [Examples](examples/basic-api.md) | [Configuration](configuration.md) | [Plugins](guides/plugins.md) | [Contributing](contributing.md) | [Updates](updates.md)

## Need help?

Check the relevant guide before opening an issue. Include your Python version,
Flaxon version, operating system, minimal reproduction, and the full error
response when reporting a problem.
