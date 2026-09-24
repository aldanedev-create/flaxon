"""FastMCP to Flaxon ASGI integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class FastMCPIntegrationError(RuntimeError):
    """Raised when a FastMCP server cannot be mounted in Flaxon."""


def _normalize_mount_path(path: str) -> str:
    if not path.startswith("/"):
        raise FastMCPIntegrationError("FastMCP mount path must start with '/'.")
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")
    return path


def mount_fastmcp(
    app: Any,
    server: Any,
    *,
    path: str = "/mcp",
    mcp_path: str = "/",
    auth: Any | None = None,
    require_auth: bool = True,
    stateless_http: bool | None = None,
    **http_options: Any,
) -> Any:
    """Mount a FastMCP HTTP server under a Flaxon path.

    ``path`` is the external Flaxon mount prefix. ``mcp_path`` is the path
    inside FastMCP and defaults to ``/`` so ``path="/mcp"`` resolves to
    ``/mcp`` rather than ``/mcp/mcp``.

    FastMCP remains responsible for MCP protocol handling, tools, resources,
    prompts, authentication, and transport behavior. Flaxon supplies the
    parent ASGI application and lifecycle. Set ``require_auth=False`` only for
    local development or explicitly isolated networks.
    """
    if not hasattr(app, "mount_asgi") or not hasattr(app, "add_lifespan_context"):
        raise FastMCPIntegrationError("The parent object must be a Flaxon application.")
    http_app_factory = getattr(server, "http_app", None)
    if not callable(http_app_factory):
        raise FastMCPIntegrationError(
            "The server must be a FastMCP instance exposing http_app(). "
            "Install FastMCP with 'pip install flaxon[mcp]'."
        )

    mount_path = _normalize_mount_path(path)
    if not mcp_path.startswith("/"):
        raise FastMCPIntegrationError("FastMCP internal path must start with '/'.")
    if require_auth and auth is None and http_options.get("auth") is None:
        raise FastMCPIntegrationError(
            "Remote FastMCP mounts require an auth provider. Pass auth=... or "
            "set require_auth=False for local development."
        )

    options = dict(http_options)
    options.setdefault("path", mcp_path)
    if auth is not None:
        options.setdefault("auth", auth)
    if stateless_http is not None:
        options.setdefault("stateless_http", stateless_http)

    mounted_app = http_app_factory(**options)
    app.mount_asgi(mount_path, mounted_app)

    lifespan = getattr(mounted_app, "lifespan", None)
    if callable(lifespan):
        app.add_lifespan_context(_lifespan_factory(mounted_app, lifespan))
    return mounted_app


def _lifespan_factory(mounted_app: Any, lifespan: Callable[..., Any]) -> Callable[[], Any]:
    """Create the zero-argument lifecycle factory expected by Flaxon."""
    def factory() -> Any:
        return lifespan(mounted_app)

    return factory
