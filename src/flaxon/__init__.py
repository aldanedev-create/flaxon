"""Flaxon, an async-first Python full-stack framework."""

from __future__ import annotations

from .version import __version__, __version_info__, version_info

from flaxon._imports import import_attribute

version = __version__

__all__ = [
    "Config",
    "ConfigurationError",
    "Flaxon",
    "FlaxonError",
    "HTMLResponse",
    "HTTPException",
    "JSONResponse",
    "LegacyJSONResponse",
    "MethodNotAllowed",
    "NotFound",
    "Query",
    "RedirectResponse",
    "Request",
    "Response",
    "Router",
    "State",
    "StreamingResponse",
    "Teloce",
    "TextResponse",
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketManager",
    "__version__",
    "__version_info__",
    "version",
    "version_info",
]


_EXPORTS = {
    "Config": "flaxon.application",
    "Flaxon": "flaxon.application",
    "State": "flaxon.application",
    "Router": "flaxon.routing",
    "Query": "flaxon.routing",
    "HTMLResponse": "flaxon.http",
    "JSONResponse": "flaxon.http",
    "LegacyJSONResponse": "flaxon.http",
    "RedirectResponse": "flaxon.http",
    "Request": "flaxon.http",
    "Response": "flaxon.http",
    "StreamingResponse": "flaxon.http",
    "TextResponse": "flaxon.http",
    "WebSocket": "flaxon.websocket",
    "WebSocketDisconnect": "flaxon.websocket",
    "WebSocketManager": "flaxon.websocket",
    "ConfigurationError": "flaxon.exceptions",
    "FlaxonError": "flaxon.exceptions",
    "HTTPException": "flaxon.exceptions",
    "MethodNotAllowed": "flaxon.exceptions",
    "NotFound": "flaxon.exceptions",
    "Jinax": "flaxon.jinax",
    "Teloce": "flaxon.teloce",
}


def __getattr__(name: str) -> object:
    """Resolve a public export only when it is requested."""
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module 'flaxon' has no attribute {name!r}")
    return import_attribute(module_name, name)
