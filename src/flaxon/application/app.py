"""The main Flaxon ASGI application."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
import secrets
import time
import traceback
import types
import typing
from collections.abc import Callable
from typing import Any
import uuid

from flaxon.admin import AdminConfig, AdminDashboard
from flaxon.debugging import Dashboard, Debugger, ErrorStore
from flaxon.dependency_injection import Container
from flaxon.exceptions import BadRequest, ConfigurationError, HTTPException
from flaxon.graphql import GraphQLSchema
from flaxon.graphql.playground import AltairPlayground, GraphiQLPlayground
from flaxon.health import HealthRegistry, LivenessProbe, ReadinessProbe, StartupProbe
from flaxon.http import HTMLResponse, JSONResponse, Request, Response
from flaxon.integrations.pydantic import is_pydantic_model_type, load_pydantic_model
from flaxon.metrics import MetricsCollector, PrometheusExporter
from flaxon.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from flaxon.plugins import PluginManager
from flaxon.routing import MISSING, Query, Router
from flaxon.sessions import SessionManager
from flaxon.sessions.backends.memory import MemoryBackend
from flaxon.validation import Schema, ValidationError
from flaxon.websocket import WebSocket, WebSocketManager

from .configuration import Config
from .lifecycle import Lifecycle
from .state import State

_UNRESOLVED = object()


class Flaxon:
    """An async-first ASGI application with route and middleware support."""

    def __init__(
        self,
        name: str,
        *,
        debug: bool | None = None,
        config: dict[str, Any] | None = None,
        openapi: bool | dict[str, Any] = False,
    ) -> None:
        self.name = name
        self.config = Config(config)
        if debug is not None:
            self.config["DEBUG"] = debug
        self.debug = bool(self.config["DEBUG"])
        
        # Core Infrastructure
        self.router = Router()
        self.state = State()
        self.lifecycle = Lifecycle()
        self.jinax: Any = None
        self.websocket_manager = WebSocketManager()
        self.error_store = ErrorStore()
        self.debugger = Debugger(debug=self.debug)
        self.plugins = PluginManager(self)
        self.container = Container()

        # Session Management
        self.sessions = SessionManager(
            backend=MemoryBackend(),
            secret_key=self.config.get_secret_key() or secrets.token_hex(32),
            cookie_secure=not self.debug,
        )

        # Middleware Stack Setup
        self._middleware: list[tuple[type[Any], dict[str, Any]]] = [
            (RequestIDMiddleware, {}),
            (SecurityHeadersMiddleware, {}),
        ]
        self._middleware_stack: Any = None

        # Health & Observability
        self.health = HealthRegistry()
        self._liveness_probe = LivenessProbe(self.health)
        self._readiness_probe = ReadinessProbe(self.health)
        self._startup_probe = StartupProbe(self.health)
        self.metrics = MetricsCollector()

        # System Endpoints
        self.router.route("/health", methods=("GET",), name="flaxon_health")(self._health_check)
        self.router.route("/health/live", methods=("GET",), name="flaxon_health_live")(self._health_live)
        self.router.route("/health/ready", methods=("GET",), name="flaxon_health_ready")(self._health_ready)
        self.router.route("/metrics", methods=("GET",), name="flaxon_metrics")(self._metrics_endpoint)

        if self.debug:
            self.router.route("/__debug__", methods=("GET",), name="flaxon_debug_dashboard")(self._debug_dashboard)

        # Admin & GraphQL Properties Initialization
        self._admin: AdminDashboard | None = None
        self._graphql_schema: GraphQLSchema | None = None
        self._openapi_generator: Any = None
        self._asgi_mounts: list[tuple[str, Any]] = []

        if openapi:
            options = dict(openapi) if isinstance(openapi, dict) else {}
            self.enable_openapi(**options)

    # ============================================================
    # SYSTEM & DIAGNOSTIC ENDPOINTS
    # ============================================================

    async def _health_check(self) -> Any:
        """Liveness-style health check covering all registered checks."""
        return (await self._liveness_probe.check()).to_response()

    async def _health_live(self) -> Any:
        """Kubernetes-style liveness probe."""
        return (await self._liveness_probe.check()).to_response()

    async def _health_ready(self) -> Any:
        """Kubernetes-style readiness probe."""
        return (await self._readiness_probe.check()).to_response()

    async def _metrics_endpoint(self) -> Any:
        """Prometheus-format metrics for whatever has been recorded on self.metrics."""
        return PrometheusExporter(self.metrics).response()

    async def _debug_dashboard(self) -> HTMLResponse:
        """Render the debug dashboard showing recent errors (debug mode only)."""
        return Dashboard(self.error_store, debug=self.debug).render()

    # ============================================================
    # ROUTING & MIDDLEWARE METHODS
    # ============================================================

    def mount_asgi(self, path: str, app: Any) -> None:
        """
        Mount a foreign ASGI application (FastAPI, Django's get_asgi_application(),
        a WSGI app wrapped with a2wsgi, etc.) at a path prefix.

        Unlike include_router()/Mount, which copies Flaxon-shaped routes, this
        delegates the entire ASGI call for matching paths straight to the mounted
        app's own __call__. Flaxon's routing, middleware, and error handling do not
        apply to that subtree -- the mounted app handles everything itself.

        Example:
            ```python
            from fastapi import FastAPI

            fastapi_app = FastAPI()

            @fastapi_app.get("/hello")
            def hello():
                return {"hello": "from fastapi"}

            app.mount_asgi("/fastapi", fastapi_app)
            ```
        """
        prefix = path.rstrip("/") if path != "/" else ""
        self._asgi_mounts.append((prefix, app))
        self._asgi_mounts.sort(key=lambda mount: -len(mount[0]))

    def route(
        self,
        path: str,
        *,
        methods: set[str] | list[str] | tuple[str, ...] = ("GET",),
        name: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        operation_id: str | None = None,
        responses: dict[str | int, Any] | None = None,
        deprecated: bool = False,
        security: list[dict[str, list[str]]] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a route with an explicit set of HTTP methods."""
        return self.router.route(
            path,
            methods=methods,
            name=name,
            summary=summary,
            description=description,
            tags=tags,
            operation_id=operation_id,
            responses=responses,
            deprecated=deprecated,
            security=security,
        )

    def get(self, path: str, *, name: str | None = None, **metadata: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a GET route."""
        return self.router.get(path, name=name, **metadata)

    def post(self, path: str, *, name: str | None = None, **metadata: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a POST route."""
        return self.router.post(path, name=name, **metadata)

    def put(self, path: str, *, name: str | None = None, **metadata: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a PUT route."""
        return self.router.put(path, name=name, **metadata)

    def patch(self, path: str, *, name: str | None = None, **metadata: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a PATCH route."""
        return self.router.patch(path, name=name, **metadata)

    def delete(self, path: str, *, name: str | None = None, **metadata: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a DELETE route."""
        return self.router.delete(path, name=name, **metadata)

    def websocket(self, path: str, *, name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a WebSocket route."""
        return self.router.websocket(path, name=name)

    def add_middleware(self, middleware_class: type[Any], **options: Any) -> None:
        """Add middleware, with first-added middleware executing outermost."""
        self._middleware.append((middleware_class, options))
        self._middleware_stack = None

    def include_router(self, router: Router, prefix: str | None = None) -> None:
        """Include routes registered on another router."""
        self.router.include_router(router, prefix=prefix)

    def url_for(self, name: str, **params: Any) -> str:
        """Build a URL for a named route."""
        return self.router.url_for(name, **params)

    def use_templates(self, engine: Any) -> None:
        """Set the template engine used by request rendering."""
        self.jinax = engine

    # ============================================================
    # ADMIN METHODS
    # ============================================================

    def enable_openapi(
        self,
        title: str = "Flaxon API",
        version: str = "1.0.0",
        description: str | None = None,
        openapi_url: str = "/openapi.json",
        spec_url: str | None = None,
        docs_url: str | None = "/docs",
        redoc_url: str | None = "/redoc",
        include_internal: bool = False,
        docs_guard: Callable[[Request], Any] | None = None,
        protect_docs: bool = False,
        persist_authorization: bool = False,
        swagger_asset_url: str = "https://unpkg.com/swagger-ui-dist@5",
        redoc_asset_url: str = "https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js",
    ) -> Any:
        """
        Enable auto-generated OpenAPI docs, derived from your routes, endpoint
        docstrings, and Schema-typed parameters -- no hand-written descriptions
        required, though you can still customize the returned generator further.
        """
        from flaxon.openapi import OpenAPIGenerator, ReDoc, SwaggerUI

        if self._openapi_generator is not None:
            return self._openapi_generator
        if spec_url is not None:
            openapi_url = spec_url
        if protect_docs and docs_guard is None:
            raise ConfigurationError("protect_docs=True requires a docs_guard callback.")

        self._openapi_generator = OpenAPIGenerator(
            title=title,
            version=version,
            description=description,
        )

        async def guarded(request: Request) -> Response | None:
            if docs_guard is None:
                return None
            result = docs_guard(request)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, Response):
                return result
            if not result:
                raise HTTPException(403, "API documentation is protected.")
            return None

        @self.router.get(openapi_url, name="flaxon_openapi_spec")
        async def openapi_spec(request: Request) -> Any:
            from flaxon.http import JSONResponse
            denied = await guarded(request)
            if denied is not None:
                return denied
            return JSONResponse(self._openapi_generator.generate_from_app(self, include_internal=include_internal))

        if docs_url:
            @self.router.get(docs_url, name="flaxon_swagger_docs")
            async def swagger_docs(request: Request) -> Any:
                denied = await guarded(request)
                if denied is not None:
                    return denied
                return SwaggerUI(
                    openapi_url=openapi_url,
                    title=title,
                    asset_url=swagger_asset_url,
                    persist_authorization=persist_authorization,
                ).render()

        if redoc_url:
            @self.router.get(redoc_url, name="flaxon_redoc_docs")
            async def redoc_docs(request: Request) -> Any:
                denied = await guarded(request)
                if denied is not None:
                    return denied
                return ReDoc(openapi_url=openapi_url, title=title, asset_url=redoc_asset_url).render()

        return self._openapi_generator

    def enable_admin(
        self,
        url_prefix: str = "/admin",
        config: AdminConfig | None = None,
        template_dir: str | None = None,
    ) -> Any:
        """Enable the admin dashboard."""
        self._admin = AdminDashboard(self, config, url_prefix, template_dir)
        return self._admin

    @property
    def admin(self) -> Any:
        """Get the admin dashboard instance."""
        return self._admin

    # ============================================================
    # GRAPHQL METHODS
    # ============================================================

    def mount_static(
        self,
        url_prefix: str,
        directory: str,
        *,
        cache_control: str | None = "public, max-age=3600",
    ) -> None:
        """Serve static files from `directory` under `url_prefix`.

        Idempotent: mounting the same url_prefix twice (e.g. because both
        AdminDashboard and CMS try to mount the shared admin static
        folder) only registers the route once.
        """
        from flaxon.static import StaticFiles

        prefix = url_prefix.rstrip("/")
        route_path = f"{prefix}/<path:filepath>"

        if any(getattr(route, "path", None) == route_path for route in self.router.routes):
            return

        handler = StaticFiles(directory, cache_control=cache_control)

        @self.router.get(route_path)
        async def static_handler(request: Request, filepath: str) -> Response:
            return await handler(request, filepath)

    def enable_graphql(        self,
        schema: GraphQLSchema | None = None,
        url: str = "/graphql",
        enable_playground: bool = True,
    ) -> GraphQLSchema:
        """Enable GraphQL support."""
        self._graphql_schema = schema or GraphQLSchema()

        @self.router.post(url)
        async def graphql_endpoint(request: Request) -> Response:
            return await self._handle_graphql(request)

        if enable_playground:
            self._register_graphql_playground(url)

        return self._graphql_schema

    async def _handle_graphql(self, request: Request) -> Response:
        """Handle GraphQL requests."""
        if self._graphql_schema is None:
            return JSONResponse(
                {"errors": [{"message": "GraphQL not configured"}]},
                status_code=500,
            )

        try:
            data = await request.json()
            query = data.get("query", "")
            variables = data.get("variables", {})
            operation_name = data.get("operationName")

            result = await self._graphql_schema.execute(
                query=query,
                variables=variables,
                context={"request": request},
                operation_name=operation_name,
            )

            return JSONResponse(result)

        except Exception as exc:
            return JSONResponse(
                {"errors": [{"message": str(exc)}]},
                status_code=500,
            )

    def _register_graphql_playground(self, url: str) -> None:
        """Register GraphQL playground routes."""
        graphiql = GraphiQLPlayground(endpoint=url)
        altair = AltairPlayground(endpoint=url)

        @self.router.get(f"{url}/graphiql")
        async def graphiql_route(request: Request) -> HTMLResponse:
            return await graphiql.render(request)

        @self.router.get(f"{url}/altair")
        async def altair_route(request: Request) -> HTMLResponse:
            return await altair.render(request)

        @self.router.get(url)
        async def playground_index(request: Request) -> HTMLResponse:
            html_path = Path(__file__).parent.parent / "graphql" / "playground" / "index.html"
            html_content = html_path.read_text()
            html = html_content.replace("{{ url }}", url)
            return HTMLResponse(html)

    @property
    def graphql(self) -> GraphQLSchema | None:
        """Get the GraphQL schema instance."""
        return self._graphql_schema

    # ============================================================
    # LIFECYCLE METHODS
    # ============================================================

    def on_startup(self, callback: Callable[..., Any]) -> Callable[..., Any]:
        """Register a startup callback."""
        return self.lifecycle.on_startup(callback)

    def on_shutdown(self, callback: Callable[..., Any]) -> Callable[..., Any]:
        """Register a shutdown callback."""
        return self.lifecycle.on_shutdown(callback)

    def add_lifespan_context(self, factory: Callable[[], Any]) -> Callable[[], Any]:
        """Register an async context manager for the application lifespan."""
        return self.lifecycle.add_lifespan_context(factory)

    # ============================================================
    # ASGI INTERFACE & HANDLERS
    # ============================================================

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle one ASGI connection."""
        if self._middleware_stack is None:
            app: Any = self._dispatch
            for middleware, options in reversed(self._middleware):
                app = middleware(app, **options)
            self._middleware_stack = app

        if scope.get("type") != "http":
            await self._middleware_stack(scope, receive, send)
            return

        try:
            await self._middleware_stack(scope, receive, send)
        except HTTPException as exc:
            response = JSONResponse(exc.to_dict(), status_code=exc.status_code)
            await response(scope, receive, send)
        except Exception as exc:
            request = Request(scope, receive, self)
            response = await self.debugger.response_for(exc, request, scope)
            if self.debug:
                self.error_store.store(
                    {
                        "error_id": str(uuid.uuid4()),
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "path": str(scope.get("path", "")),
                        "timestamp": time.time(),
                    }
                )
            await response(scope, receive, send)

    async def _dispatch(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        scope["app"] = self

        if scope.get("type") in ("http", "websocket") and self._asgi_mounts:
            path = str(scope.get("path", "/"))
            for prefix, mounted_app in self._asgi_mounts:
                if path == prefix or path.startswith(f"{prefix}/"):
                    sub_scope = dict(scope)
                    sub_scope["path"] = path[len(prefix):] or "/"
                    sub_scope["root_path"] = scope.get("root_path", "") + prefix
                    await mounted_app(sub_scope, receive, send)
                    return

        match scope.get("type"):
            case "http":
                await self._handle_http(scope, receive, send)
            case "websocket":
                await self._handle_websocket(scope, receive, send)
            case "lifespan":
                await self._handle_lifespan(receive, send)
            case value:
                raise RuntimeError(f"Unsupported ASGI scope type: {value!r}")

    async def _handle_http(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        request = Request(scope, receive, self)

        # Session Middleware Initialization
        session_cookie = request.cookies.get(self.sessions.cookie_name)
        session_is_new = True
        if session_cookie:
            parsed = self.sessions.parse_cookie(session_cookie)
            if parsed:
                existing = await self.sessions.get(parsed[0])
                if existing is not None and not existing.is_expired():
                    request.session = existing
                    session_is_new = False
        if session_is_new:
            request.session = await self.sessions.create()

        # Routing and Execution
        try:
            matched = self.router.match(request.path, request.method)
            request.path_params = matched.params
            result = await self._invoke(matched.route.endpoint, request, matched.params)
            response = Response.from_value(result)
        except HTTPException as exc:
            response = JSONResponse(exc.to_dict(), status_code=exc.status_code)
        except Exception as exc:
            response = await self.debugger.response_for(exc, request, scope)
            if self.debug:
                self.error_store.store(
                    {
                        "error_id": str(scope.get("flaxon.request_id") or uuid.uuid4()),
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "path": request.path,
                        "timestamp": time.time(),
                    }
                )

        # Save session header updates
        if session_is_new or request.session.is_dirty():
            await self.sessions.save(request.session)
            response.headers.add("set-cookie", self.sessions.create_cookie(request.session))

        if request.method == "HEAD":
            response.body = b""
            response.headers["content-length"] = "0"

        await response(scope, receive, send)

    async def _invoke(self, endpoint: Callable[..., Any], request: Request | WebSocket, params: dict[str, Any]) -> Any:
        signature = inspect.signature(endpoint)
        try:
            hints = typing.get_type_hints(endpoint)
        except Exception:
            hints = {}
        container_kwargs = self.container.resolve(endpoint)
        kwargs: dict[str, Any] = {}
        for name, parameter in signature.parameters.items():
            annotation = hints.get(name, parameter.annotation)
            if name in params:
                kwargs[name] = params[name]
            elif name in {"request", "socket", "websocket"}:
                kwargs[name] = request
            elif name in container_kwargs:
                kwargs[name] = container_kwargs[name]
            elif isinstance(parameter.default, Query):
                kwargs[name] = self._resolve_query_parameter(request, name, annotation, parameter.default)
            else:
                body_value = await self._resolve_body_parameter(request, annotation)
                if body_value is not _UNRESOLVED:
                    kwargs[name] = body_value
                elif parameter.default is not inspect.Parameter.empty:
                    continue
                else:
                    raise TypeError(f"Cannot resolve endpoint parameter {name!r}")
        result = endpoint(**kwargs)
        return await result if inspect.isawaitable(result) else result

    @staticmethod
    def _resolve_query_parameter(request: Request | WebSocket, name: str, annotation: Any, declaration: Query) -> Any:
        """Read and coerce a declared query parameter without extra dependencies."""
        if not isinstance(request, Request):
            if declaration.default is MISSING:
                raise TypeError(f"Query parameter {name!r} requires an HTTP request")
            return declaration.default

        key = declaration.alias or name
        if key not in request.query:
            if declaration.default is MISSING:
                raise ValidationError({name: ["This query parameter is required."]})
            return declaration.default

        value: Any = request.query[key]
        target = annotation
        origin = typing.get_origin(target)
        if origin in (typing.Union, types.UnionType):
            target = next((item for item in typing.get_args(target) if item is not type(None)), str)
        try:
            if target is bool:
                normalized = str(value).strip().lower()
                if normalized in {"1", "true", "yes", "on"}:
                    converted = True
                elif normalized in {"0", "false", "no", "off"}:
                    converted = False
                else:
                    raise ValueError("expected a boolean")
            elif target is int:
                converted = int(value)
            elif target is float:
                converted = float(value)
            elif target is str or target is inspect.Parameter.empty or target is Any:
                converted = value
            else:
                converted = target(value)
            if declaration.ge is not None and converted < declaration.ge:
                raise ValueError(f"must be greater than or equal to {declaration.ge}")
            if declaration.le is not None and converted > declaration.le:
                raise ValueError(f"must be less than or equal to {declaration.le}")
            if declaration.min_length is not None and len(converted) < declaration.min_length:
                raise ValueError(f"must contain at least {declaration.min_length} characters")
            if declaration.max_length is not None and len(converted) > declaration.max_length:
                raise ValueError(f"must contain no more than {declaration.max_length} characters")
            return converted
        except (TypeError, ValueError) as exc:
            raise ValidationError({name: [f"Invalid value for query parameter '{key}'."]}) from exc

    async def _resolve_body_parameter(self, request: Request | WebSocket, annotation: Any) -> Any:
        """Resolve an optional Pydantic or native Flaxon body schema."""
        is_native_schema = isinstance(annotation, type) and issubclass(annotation, Schema)
        if not isinstance(request, Request) or not (is_pydantic_model_type(annotation) or is_native_schema):
            return _UNRESOLVED
        try:
            body = await request.json()
        except json.JSONDecodeError as exc:
            raise BadRequest("Request body must be valid JSON.") from exc
        if is_pydantic_model_type(annotation):
            return load_pydantic_model(annotation, body)
        return annotation.load(body)

    async def _handle_websocket(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        socket = WebSocket(scope, receive, send, self.websocket_manager)
        try:
            matched = self.router.match_websocket(str(scope.get("path", "/")))
            socket.path_params = matched.params
            await self._invoke(matched.route.endpoint, socket, matched.params)
        except HTTPException:
            await socket.close(code=4404, reason="WebSocket route not found")
        except Exception as exc:
            if self.debug:
                print(f"\n--- Unhandled WebSocket error on {scope.get('path')} ---")
                traceback.print_exc()
                self.error_store.store(
                    {
                        "error_id": str(uuid.uuid4()),
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "path": str(scope.get("path", "")),
                        "timestamp": time.time(),
                    }
                )
            await socket.close(code=1011, reason="Internal server error")

    async def _handle_lifespan(self, receive: Any, send: Any) -> None:
        while True:
            message = await receive()
            if message.get("type") == "lifespan.startup":
                try:
                    await self.lifecycle.startup()
                    await self.plugins.startup()
                except Exception as exc:
                    await send({"type": "lifespan.startup.failed", "message": str(exc)})
                else:
                    self._startup_probe.mark_started()
                    self._readiness_probe.mark_ready()
                    await send({"type": "lifespan.startup.complete"})
            elif message.get("type") == "lifespan.shutdown":
                self._readiness_probe.mark_not_ready()
                try:
                    await self.plugins.shutdown()
                    await self.lifecycle.shutdown()
                except Exception as exc:
                    await send({"type": "lifespan.shutdown.failed", "message": str(exc)})
                else:
                    await send({"type": "lifespan.shutdown.complete"})
                return
