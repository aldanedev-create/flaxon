"""Store feature module with Flaxon routes and FastMCP tools."""

from typing import Any

from fastmcp import FastMCP

from flaxon.integrations.fastmcp import mount_fastmcp
from flaxon.modules import FlaxonModule

store = FlaxonModule("store")
mcp = FastMCP("Store Tools")


@store.get("/status")
async def store_status() -> dict[str, str]:
    """Return the normal HTTP status for the store feature."""
    return {"status": "healthy", "feature": "store"}


@mcp.tool
async def health_summary() -> dict[str, str]:
    """Return a health summary for an MCP client."""
    return {"status": "healthy", "framework": "flaxon"}


def install_store(app: Any, *, allow_unauthenticated_local_mcp: bool = False) -> None:
    """Mount the store HTTP module and its MCP endpoint.

    The unauthenticated option is only for this local example. Production
    applications should pass an auth provider and keep the secure default.
    """
    app.mount_module(store, prefix="/store")
    mount_fastmcp(
        app,
        mcp,
        path="/mcp",
        require_auth=not allow_unauthenticated_local_mcp,
    )
