# Flaxon documentation

Flaxon is an async-first ASGI framework for HTTP APIs, WebSockets, and
server-rendered applications. It is deliberately technology-neutral: Flaxon
handles the web boundary, while your application chooses its database, queue,
frontend, and deployment platform.

## What you can build

- JSON APIs with typed route parameters and schema validation.
- HTML applications with Jinax (the optional Jinja2-based template engine).
- WebSocket features such as chat, live dashboards, and room broadcasts.
- Authenticated applications using sessions, JWTs, API keys, roles, and
  permissions.
- Background work with tasks, workers, retries, schedules, and result storage.
- APIs with OpenAPI, Swagger UI, ReDoc, GraphQL, health checks, metrics, and
  plugins.

## Capability map

| Need | Flaxon capability | Start with |
|---|---|---|
| HTTP endpoints | `Flaxon`, `Router`, typed path parameters, responses | [Routing](guides/routing.md) and [HTTP](api/http.md) |
| Large application composition | `FlaxonModule`, mount-time prefixes, feature installers | [Modules](guides/Modules.md) and [Scaling](guides/scaling.md) |
| JSON input validation | `Schema` and `fields.*Field` | [Validation](guides/validation.md) |
| Pydantic request models | Optional Pydantic adapter | [Pydantic](guides/pydantic.md) |
| Browser security and request policy | CORS, trusted hosts, body limits, security headers, request IDs | [Middleware](guides/middleware.md) and [Security](security.md) |
| Accounts and access control | Sessions, JWT, API keys, authentication, roles, permissions | [Authentication](guides/authentication.md) and [Authorization](guides/authorization.md) |
| HTML pages | Jinax templates, autoescaping, template inheritance | [Jinax](guides/jinax.md) |
| Real-time features | WebSocket routes, JSON messages, rooms, broadcasts | [WebSockets](guides/websockets.md) |
| Data access | Database manager, adapters, transactions, repositories, migrations | [Databases](guides/databases.md) |
| Background work | Tasks, workers, queues, retries, schedules, results | [Tasks](guides/tasks.md) |
| API contracts | OpenAPI, Swagger UI, ReDoc, GraphQL | [GraphQL](guides/graphql.md) and [API reference](api/application.md) |
| Operations | Lifespan hooks, health endpoints, Prometheus-format metrics, logging | [Deployment](deployment.md) and [Performance](performance.md) |
| Extensibility | Plugins and lifecycle hooks | [Plugins](guides/plugins.md) |
| Companion integrations | AI, mobile, frontend, observability, testing, and migration projects | [Ecosystem](ecosystem.md) |
| MCP tools | Optional FastMCP ASGI mounting and lifecycle integration | [FastMCP](guides/fastmcp.md) |
| Test automation | Sync HTTP and async WebSocket test clients | [Testing](guides/testing.md) |

Some features require optional packages or external infrastructure. For
example, Jinax requires Jinja2, production serving requires an ASGI server,
and Redis-backed components require Redis plus its Python client. The relevant
guide calls out those requirements; install only the extras your application
uses.

Pydantic request models and FastMCP are also optional integrations. Install
`flaxon[pydantic]` or `flaxon[mcp]` only when your application uses them.

## Start here

1. [Install Flaxon](installation.md) and complete the [Quick Start](quickstart.md).
2. Learn the request boundary: [routing](guides/routing.md),
   [requests](guides/requests.md), [responses](guides/responses.md), and
   [validation](guides/validation.md).
3. Add the capabilities your application needs: [middleware](guides/middleware.md),
   [authentication](guides/authentication.md), [WebSockets](guides/websockets.md),
   [Jinax](guides/jinax.md), [tasks](guides/tasks.md), and
   [databases](guides/databases.md).
4. When the project grows, follow the [large-application guide](guides/scaling.md)
   before adding more pages or endpoints.

## Choose the next guide

Use this path to move from a first API to a production application. Each link
points to a maintained guide or runnable example in this repository.

| You want to build | Continue with |
|---|---|
| A structured API | [Routing](guides/routing.md), [Requests](guides/requests.md), [Responses](guides/responses.md), and [Validation](guides/validation.md) |
| Automatic API documentation | [OpenAPI, Swagger UI, and ReDoc](guides/openapi.md) |
| A modular API with Pydantic | [Modules](guides/Modules.md), [Pydantic](guides/pydantic.md), and the [Pydantic example](examples/pydantic-api.md) |
| MCP tools for an existing app | [FastMCP](guides/fastmcp.md), [Modules](guides/Modules.md), and the [FastMCP example](examples/fastmcp-app.md) |
| A server-rendered site | [Jinax](guides/jinax.md) and [Jinax API reference](api/jinax.md) |
| Login and permissions | [Authentication](guides/authentication.md) and [Authorization](guides/authorization.md) |
| Admin and CMS workflows | [Admin and CMS](guides/admin-cms.md), [Admin production](guides/admin-production.md), and [Admin guide](admin-guide.md) |
| Database-backed content | [Databases](guides/databases.md) and [Migration guide](migration-guide.md) |
| Background work | [Tasks](guides/tasks.md) and [Scaling](guides/scaling.md) |
| Tests and diagnostics | [Testing](guides/testing.md) and [Debugging](guides/debugging.md) |
| Production deployment | [Deployment](deployment.md), [Security](security.md), and [Performance](performance.md) |
| Mobile or frontend clients | [Mobile backends](guides/mobile-developement.md) and [Frontend integration](examples/frontend-integration.md) |

**More developer navigation:** [API reference](api/application.md) | [Examples](examples/basic-api.md) | [Configuration](configuration.md) | [Plugins](guides/plugins.md) | [Contributing](contributing.md) | [Updates](updates.md)

## Supported public field classes

Validation fields use their full class names. Copy these names exactly:

`StrField`, `IntField`, `FloatField`, `BoolField`, `EmailField`, `DateField`,
`DateTimeField`, `DecimalField`, `UUIDField`, `ListField`, `ChoiceField`,
`NestedField`, and `AnyField`.

```python
from flaxon.validation import Schema, fields


class CreateUser(Schema):
    name = fields.StrField(required=True, min_length=2)
    email = fields.EmailField(required=True)
    age = fields.IntField(minimum=13, maximum=120)
```

## Production boundary

Flaxon is an ASGI application, so run it with the `flaxon run` CLI or an ASGI
server such as Uvicorn. For production, use a reverse proxy, disable debug
mode, keep workers stateless, and move shared state out of process. See
[Deployment](deployment.md), [Security](security.md), and
[Performance](performance.md).
