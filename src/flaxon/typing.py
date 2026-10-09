"""Type definitions for Flaxon.

This module contains type aliases and protocol definitions used throughout
the framework.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, Union, runtime_checkable

if TYPE_CHECKING:
    from .http import Response  # <-- Response import for type checker

# ============================================================
# Basic Type Aliases
# ============================================================

# JSON-compatible types
JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union[JSONPrimitive, dict[str, "JSONValue"], list["JSONValue"]]
JSONObject = dict[str, JSONValue]
JSONArray = list[JSONValue]

# Headers type
HeadersType = Union[
    dict[str, str],
    list[tuple[bytes, bytes]],
    tuple[tuple[bytes, bytes], ...],
]

# Query parameters type
QueryParamsType = dict[str, Union[str, list[str]]]

# Cookies type
CookiesType = dict[str, str]

# ============================================================
# Callback Types
# ============================================================

# Async callable that returns nothing
AsyncVoidCallback = Callable[[], Awaitable[None]]

# Sync callable that returns nothing
SyncVoidCallback = Callable[[], None]

# Async or sync callable that returns nothing
VoidCallback = Union[AsyncVoidCallback, SyncVoidCallback]

# Endpoint function type
Endpoint = Callable[
    ..., Union[JSONValue, "Response", Awaitable[Union[JSONValue, "Response"]]]
]

# WebSocket endpoint type
WebSocketEndpoint = Callable[..., Union[None, Awaitable[None]]]

# Middleware callable type
MiddlewareCallable = Callable[
    [
        dict[str, Any],
        Callable[..., Awaitable[dict[str, Any]]],
        Callable[..., Awaitable[None]],
    ],
    Awaitable[None],
]

# ============================================================
# Context Types
# ============================================================

# ASGI scope type
ScopeType = dict[str, Any]

# ASGI receive callable
ReceiveType = Callable[[], Awaitable[dict[str, Any]]]

# ASGI send callable
SendType = Callable[[dict[str, Any]], Awaitable[None]]

# ASGI application type
ASGIApp = Callable[[ScopeType, ReceiveType, SendType], Awaitable[None]]

# ============================================================
# Protocol Definitions
# ============================================================


@runtime_checkable
class SupportsStr(Protocol):
    """Protocol for objects that can be converted to string."""

    def __str__(self) -> str: ...


@runtime_checkable
class SupportsRepr(Protocol):
    """Protocol for objects that can be converted to representation."""

    def __repr__(self) -> str: ...


@runtime_checkable
class SupportsJSON(Protocol):
    """Protocol for objects that can be converted to JSON."""

    def to_json(self) -> JSONValue: ...


@runtime_checkable
class SupportsDict(Protocol):
    """Protocol for objects that can be converted to dict."""

    def to_dict(self) -> dict[str, Any]: ...


# ============================================================
# Type Variables
# ============================================================

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)

# Handler type variable
HandlerType = TypeVar("HandlerType", bound=Callable[..., Any])

# ============================================================
# HTTP Types
# ============================================================

HTTPMethod = Union[str, Callable[..., Any]]
HTTPMethods = Union[list[str], tuple[str, ...], set[str]]

# ============================================================
# Validation Types
# ============================================================


class SchemaType:
    """Protocol for validation schemas."""

    __fields__: dict[str, FieldType]

    @classmethod
    def load(cls, data: dict[str, Any]) -> SchemaType: ...

    def to_dict(self) -> dict[str, Any]: ...


FieldType = Any  # Forward reference to fields.Field

# ============================================================
# Route Types
# ============================================================

RoutePath = str
RouteName = str
RouteMethods = set[str]

# ============================================================
# Application Types
# ============================================================

ConfigDict = dict[str, Any]
AppState = dict[str, Any]

# ============================================================
# Event Types
# ============================================================

EventListener = Callable[[Any], Union[None, Awaitable[None]]]
EventDispatcher = Callable[[str, Any], Awaitable[None]]

# ============================================================
# Plugin Types
# ============================================================

PluginHook = Callable[..., Union[None, Awaitable[None]]]
PluginRegistry = dict[str, dict[str, PluginHook]]

# ============================================================
# Export
# ============================================================

__all__ = [
    # Basic types
    "JSONPrimitive",
    "JSONValue",
    "JSONObject",
    "JSONArray",
    "HeadersType",
    "QueryParamsType",
    "CookiesType",
    # Callbacks
    "AsyncVoidCallback",
    "SyncVoidCallback",
    "VoidCallback",
    "Endpoint",
    "WebSocketEndpoint",
    "MiddlewareCallable",
    # Context types
    "ScopeType",
    "ReceiveType",
    "SendType",
    "ASGIApp",
    # Protocols
    "SupportsStr",
    "SupportsRepr",
    "SupportsJSON",
    "SupportsDict",
    # Type variables",
    "T",
    "T_co",
    "T_contra",
    "HandlerType",
    # HTTP types
    "HTTPMethod",
    "HTTPMethods",
    # Validation types
    "SchemaType",
    "FieldType",
    # Route types
    "RoutePath",
    "RouteName",
    "RouteMethods",
    # Application types
    "ConfigDict",
    "AppState",
    # Event types
    "EventListener",
    "EventDispatcher",
    # Plugin types
    "PluginHook",
    "PluginRegistry",
]
