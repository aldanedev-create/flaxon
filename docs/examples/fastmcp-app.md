# FastMCP Example

This runnable example puts normal Flaxon routes and FastMCP tools in one
feature module. The root application composes the feature and does not start a
second server.

```text
examples/fastmcp_app/
|-- app.py
`-- modules/
    `-- store.py
```

Install and run it from the repository root:

```bash
python -m pip install "flaxon[mcp]"
flaxon run examples.fastmcp_app.app:app --reload
```

The example exposes:

| URL | Purpose |
|---|---|
| `/store/status` | Normal Flaxon HTTP route |
| `/mcp` | FastMCP Streamable HTTP endpoint |

The example explicitly allows unauthenticated MCP access for local testing.
For a deployed application, pass an authentication provider to
`mount_fastmcp()` and keep `require_auth=True`. For multiple workers, use
stateless HTTP mode and shared storage for application data and events.

Source files: [app.py](https://github.com/aldanedev-create/Flaxon-Backend-Framework/tree/main/examples/fastmcp_app)
