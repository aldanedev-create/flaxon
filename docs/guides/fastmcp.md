# FastMCP Integration

FastMCP is an optional integration for exposing Flaxon application operations
as Model Context Protocol tools, resources, and prompts. It is useful when the
same application also provides normal HTTP, GraphQL, WebSocket, admin, or CMS
features.

## Install

```bash
python -m pip install "flaxon[mcp]"
```

FastMCP and Starlette are not required by Flaxon core.

## Mount an MCP server

```python
from fastmcp import FastMCP

from flaxon import Flaxon
from flaxon.integrations.fastmcp import mount_fastmcp

app = Flaxon("store", debug=True)
mcp = FastMCP("Store Tools")


@mcp.tool
async def find_product(name: str) -> dict[str, str | bool]:
    """Find a product in the store catalog."""
    return {"name": name, "available": True}


mount_fastmcp(app, mcp, path="/mcp", require_auth=False)
```

The MCP endpoint is available at `/mcp`; the rest of the Flaxon routes remain
unchanged. `require_auth=False` is explicit here because this is a local
development example. Remote deployments should provide an auth provider.

## Authentication and production configuration

Pass FastMCP HTTP options through the adapter:

```python
mount_fastmcp(
    app,
    mcp,
    path="/mcp",
    auth=auth_provider,
    require_auth=True,
    host_origin_protection=True,
    allowed_hosts=["api.example.com"],
    allowed_origins=["https://console.example.com"],
)
```

Do not expose remote MCP tools without authentication. Treat tool calls as
application operations: apply authorization, rate limits, input validation,
audit logging, and business rules before allowing side effects.

## Multiple workers

FastMCP's default Streamable HTTP sessions are process-local. For multiple
workers or multiple instances, enable stateless mode and put application data
and event storage in shared infrastructure:

```python
mount_fastmcp(app, mcp, path="/mcp", stateless_http=True)
```

Configure shared Redis or database storage for any application state that must
survive worker changes.

## Lifecycle behavior

`mount_fastmcp()` registers the FastMCP HTTP app's lifespan with Flaxon. The
MCP session manager is initialized during Flaxon startup and closed during
Flaxon shutdown. Do not call `mcp.run()` inside a Flaxon endpoint or startup
handler; the mounted ASGI application owns the protocol lifecycle.

## Keep API boundaries clear

- Use Flaxon routes for normal HTTP APIs.
- Use GraphQL for typed graph queries.
- Use WebSockets for application real-time features.
- Use FastMCP for tools and resources consumed by MCP clients.

FastMCP remains the source of truth for MCP protocol behavior; this integration
only provides mounting and lifecycle composition.

## Use FastMCP from a large application module

Keep MCP tools with the feature they operate on. A module should export an
installer function; the application factory supplies authentication and mounts
the feature. This avoids starting a second server and makes the same business
service reusable from HTTP and MCP.

```python
# app/modules/ai_tools/module.py
from typing import Any

from fastmcp import FastMCP

from flaxon.integrations.fastmcp import mount_fastmcp

mcp = FastMCP("Store Tools")


@mcp.tool
async def find_product(name: str) -> dict[str, str | bool]:
    return {"name": name, "available": True}


def install_ai_tools(app: Any, auth_provider: Any) -> None:
    mount_fastmcp(
        app,
        mcp,
        path="/mcp",
        auth=auth_provider,
        require_auth=True,
        stateless_http=True,
    )
```

Compose it with the other modules:

```python
# app/main.py
from flaxon import Flaxon

from app.auth import auth_provider
from app.modules.ai_tools.module import install_ai_tools
from app.modules.catalog.module import install_catalog


def create_app() -> Flaxon:
    app = Flaxon("store", debug=False)
    install_catalog(app)
    install_ai_tools(app, auth_provider)
    return app


app = create_app()
```

`auth_provider` above is your application's configured FastMCP-compatible
provider. Keep `require_auth=True` outside local development. `stateless_http`
is useful for multiple workers, but shared application data and event storage
still belong in a database or Redis. Never call `mcp.run()` in this layout.

The complete local example is `examples/fastmcp_app/`. Install and run it with:

```bash
python -m pip install "flaxon[mcp]"
flaxon run examples.fastmcp_app.app:app --reload
```
