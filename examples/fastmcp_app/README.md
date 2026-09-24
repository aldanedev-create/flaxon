# FastMCP integration

Install the optional integration:

```bash
python -m pip install "flaxon[mcp]"
```

Run the combined modular Flaxon and FastMCP application:

```bash
flaxon run examples.fastmcp_app.app:app --reload
```

The normal Flaxon health endpoint remains at `/health`; the example's store
status endpoint is `/store/status`. The MCP Streamable HTTP endpoint is
mounted at `/mcp`.

The store feature is defined in `modules/store.py`. It owns the normal
Flaxon route, the FastMCP tools, and one `install_store()` function. The root
`app.py` only creates the application and mounts that feature.

This example explicitly enables unauthenticated MCP for local testing. In a
real deployment, change the installer to pass an authentication provider and
leave `require_auth=True`.

For multiple workers, configure FastMCP's stateless HTTP mode and use shared
external state for any event storage or application data.
