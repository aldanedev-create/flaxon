"""Flaxon, an async-first Python backend framework."""

from __future__ import annotations

from .version import __version__, __version_info__, version_info

version = __version__

__all__ = [
    "Config",
    "ConfigurationError",
    "Flaxon",
    "FlaxonError",
    "HTMLResponse",
    "HTTPException",
    "JSONResponse",
    "MethodNotAllowed",
    "NotFound",
    "RedirectResponse",
    "Request",
    "Response",
    "Query",
    "Router",
    "State",
    "StreamingResponse",
    "TextResponse",
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketManager",
    "__version__",
    "__version_info__",
    "version",
    "version_info",
]


def __getattr__(name: str) -> object:
    """Lazily import public objects to keep package metadata importable."""
    if name in {"Config", "Flaxon", "State"}:
        from .application import Config, Flaxon, State

        return {"Config": Config, "Flaxon": Flaxon, "State": State}[name]
    if name == "Router":
        from .routing import Router

        return Router
    if name == "Query":
        from .routing import Query

        return Query
    if name in {
        "HTMLResponse",
        "JSONResponse",
        "RedirectResponse",
        "Request",
        "Response",
        "StreamingResponse",
        "TextResponse",
    }:
        from . import http

        return getattr(http, name)
    if name in {"WebSocket", "WebSocketDisconnect", "WebSocketManager"}:
        from . import websocket

        return getattr(websocket, name)
    if name in {
        "ConfigurationError",
        "FlaxonError",
        "HTTPException",
        "MethodNotAllowed",
        "NotFound",
    }:
        from . import exceptions

        return getattr(exceptions, name)
    if name == "Jinax":
        from .jinax import Jinax

        return Jinax
    raise AttributeError(f"module 'flaxon' has no attribute {name!r}")
