"""HTTP and WebSocket route registry."""

from __future__ import annotations

import logging
import re
from bisect import insort
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from heapq import merge
from typing import Any

from flaxon.exceptions import MethodNotAllowed, NotFound

from .route import Route, WebSocketRoute

logger = logging.getLogger(__name__)


@dataclass
class RouteMatch:
    """The route and extracted values selected for a request."""

    route: Route | WebSocketRoute
    params: dict[str, Any]


@dataclass
class _PrefixNode:
    """Candidates below a literal path prefix; parameters stay regex matched."""

    children: dict[str, _PrefixNode] = field(default_factory=dict)
    routes: list[Route] = field(default_factory=list)


class Router:
    """Register routes and resolve them by request path and method."""

    def __init__(self, prefix: str = "") -> None:
        self.prefix = prefix.rstrip("/")
        self.routes: list[Route] = []
        self.websocket_routes: list[WebSocketRoute] = []
        self._static_routes: dict[str, list[Route]] = {}
        self._dynamic_prefixes = _PrefixNode()
        self._registration_order = 0
        self._collision_buckets: dict[tuple[str, ...], list[Route]] = {}
        self._pattern_collision_buckets: dict[tuple[int, str], list[Route]] = {}
        self._static_collision_buckets: dict[tuple[int, str], list[Route]] = {}

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
        """Return a decorator that registers an HTTP endpoint."""

        def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
            route = Route(
                self._path(path),
                endpoint,
                {method.upper() for method in methods},
                name or endpoint.__name__,
                summary=summary,
                description=description,
                tags=list(tags) if tags else None,
                operation_id=operation_id,
                responses=dict(responses) if responses else None,
                deprecated=deprecated,
                security=list(security) if security is not None else None,
            )
            route.registration_order = self._registration_order
            self._registration_order += 1
            self._warn_collisions(route)
            self.routes.append(route)
            self._index_route(route)
            return endpoint

        return decorator

    def get(
        self, path: str, *, name: str | None = None, **metadata: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register an HTTP GET endpoint."""
        return self.route(path, methods={"GET"}, name=name, **metadata)

    def post(
        self, path: str, *, name: str | None = None, **metadata: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register an HTTP POST endpoint."""
        return self.route(path, methods={"POST"}, name=name, **metadata)

    def put(
        self, path: str, *, name: str | None = None, **metadata: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register an HTTP PUT endpoint."""
        return self.route(path, methods={"PUT"}, name=name, **metadata)

    def patch(
        self, path: str, *, name: str | None = None, **metadata: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register an HTTP PATCH endpoint."""
        return self.route(path, methods={"PATCH"}, name=name, **metadata)

    def delete(
        self, path: str, *, name: str | None = None, **metadata: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register an HTTP DELETE endpoint."""
        return self.route(path, methods={"DELETE"}, name=name, **metadata)

    def websocket(
        self, path: str, *, name: str | None = None
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Return a decorator that registers a WebSocket endpoint."""

        def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
            self.websocket_routes.append(
                WebSocketRoute(self._path(path), endpoint, name or endpoint.__name__)
            )
            return endpoint

        return decorator

    def match(self, path: str, method: str) -> RouteMatch:
        """Find the HTTP route matching a path and method."""
        method = method.upper()
        exact = self._static_routes.get(path, ())
        for route in exact:
            if method in route.methods:
                return RouteMatch(route, {})
        method_allowed = bool(exact)
        candidates = self._candidates(path)
        for route in candidates:
            params = route.match(path)
            if params is None:
                continue
            if method in route.methods:
                return RouteMatch(route, params)
            method_allowed = True
        if method_allowed:
            raise MethodNotAllowed()
        raise NotFound()

    def _index_route(self, route: Route) -> None:
        if not route.parameters:
            self._static_routes.setdefault(route.path, []).append(route)
            return
        node = self._dynamic_prefixes
        # Stop before the first parameter, including mixed literal/parameter
        # segments. Custom converters may span slashes, so never index beyond it.
        prefix = route.path.split("<", 1)[0]
        literal_segments = prefix.split("/")[:-1]
        for segment in literal_segments:
            node = node.children.setdefault(segment, _PrefixNode())
        insort(node.routes, route, key=self._priority)

    def _candidates(self, path: str) -> Iterator[Route]:
        node = self._dynamic_prefixes
        groups = [node.routes] if node.routes else []
        for segment in path.split("/"):
            child = node.children.get(segment)
            if child is None:
                break
            node = child
            if node.routes:
                groups.append(node.routes)
        if len(groups) == 1:
            return iter(groups[0])
        return merge(*groups, key=self._priority)

    def match_websocket(self, path: str) -> RouteMatch:
        """Find the WebSocket route matching a path."""
        for route in self.websocket_routes:
            params = route.match(path)
            if params is not None:
                return RouteMatch(route, params)
        raise NotFound()

    def include_router(self, router: Router, prefix: str | None = None) -> None:
        """Copy routes and optionally apply a new mount prefix."""
        mount = (prefix or "").rstrip("/")
        source_prefix = router.prefix.rstrip("/")

        def mounted_path(source_path: str) -> str:
            path = source_path
            if (
                prefix is not None
                and source_prefix
                and (path == source_prefix or path.startswith(source_prefix + "/"))
            ):
                path = path[len(source_prefix) :] or "/"
            if prefix is not None:
                path = f"{mount}{path}" if path.startswith("/") else f"{mount}/{path}"
            return path

        for source in router.routes:
            path = mounted_path(source.path)
            route = Route(
                path,
                source.endpoint,
                set(source.methods),
                source.name,
                summary=source.summary,
                description=source.description,
                tags=list(source.tags) if source.tags else None,
                operation_id=source.operation_id,
                responses=dict(source.responses) if source.responses else None,
                deprecated=source.deprecated,
                security=list(source.security) if source.security is not None else None,
            )
            route.registration_order = self._registration_order
            self._registration_order += 1
            self._warn_collisions(route)
            self.routes.append(route)
            self._index_route(route)
        for websocket in router.websocket_routes:
            self.websocket_routes.append(
                WebSocketRoute(mounted_path(websocket.path), websocket.endpoint, websocket.name)
            )

    def url_for(self, name: str, **params: Any) -> str:
        """Build a URL from a named route and its parameters."""
        for route in self.routes:
            if route.name == name:
                path = route.path
                for parameter, _converter in route.parameters:
                    marker = next(
                        match.group(0)
                        for match in re.finditer(
                            r"<(?:(?:[a-zA-Z_][a-zA-Z0-9_]*):)?" + parameter + r">", path
                        )
                    )
                    path = path.replace(marker, str(params[parameter]))
                return path
        raise KeyError(f"No route named {name!r}")

    def _path(self, path: str) -> str:
        return f"{self.prefix}{path}" if self.prefix else path

    @staticmethod
    def _priority(route: Route) -> tuple[int, int, int, int]:
        literals, parameters, segments = route.specificity
        return (-literals, parameters, -segments, route.registration_order)

    @staticmethod
    def _first_segment(path: str) -> str:
        segment = next((part for part in path.strip("/").split("/") if part), "")
        return "*" if "<" in segment else segment

    def _collision_candidates(self, route: Route, shape: tuple[str, ...]) -> list[Route]:
        candidates: dict[int, Route] = {}
        for existing in self._collision_buckets.get(shape, []):
            candidates[id(existing)] = existing
        if route.parameters:
            static_key = (len(shape), shape[0] if shape and shape[0] != "*" else "")
            for existing in self._static_collision_buckets.get(static_key, []):
                candidates[id(existing)] = existing
            if shape and shape[0] != "*":
                for existing in self._static_collision_buckets.get((len(shape), "*"), []):
                    candidates[id(existing)] = existing
        else:
            pattern_keys = [(len(shape), shape[0] if shape else "")]
            if shape and shape[0] != "*":
                pattern_keys.append((len(shape), "*"))
            for key in pattern_keys:
                for existing in self._pattern_collision_buckets.get(key, []):
                    candidates[id(existing)] = existing
        return list(candidates.values())

    def _warn_collisions(self, route: Route) -> None:
        shape = self._collision_shape(route.path)
        for existing in self._collision_candidates(route, shape):
            if existing.methods.intersection(route.methods) and self._patterns_overlap(existing, route):
                logger.warning(
                    "Ambiguous route collision: %s %s overlaps %s %s; specificity will decide",
                    ",".join(sorted(route.methods)),
                    route.path,
                    ",".join(sorted(existing.methods)),
                    existing.path,
                )
        collision_key = (len(shape), shape[0] if shape and shape[0] != "*" else "*")
        if route.parameters:
            self._pattern_collision_buckets.setdefault(collision_key, []).append(route)
        else:
            self._static_collision_buckets.setdefault((len(shape), shape[0] if shape else ""), []).append(
                route
            )
            self._collision_buckets.setdefault(shape, []).append(route)

    @staticmethod
    def _collision_shape(path: str) -> tuple[str, ...]:
        """Build an exact literal/parameter shape for collision indexing."""
        parts = [part for part in path.strip("/").split("/") if part]
        if not parts:
            return ()
        literal = re.compile(r"^<(?:(?:[a-zA-Z_][a-zA-Z0-9_]*):)?[a-zA-Z_][a-zA-Z0-9_]*>$")
        return tuple(part if not literal.fullmatch(part) else "*" for part in parts)

    @staticmethod
    def _patterns_overlap(left: Route, right: Route) -> bool:
        if left.path == right.path:
            return True
        left_parts = [part for part in left.path.strip("/").split("/") if part]
        right_parts = [part for part in right.path.strip("/").split("/") if part]
        if len(left_parts) != len(right_parts):
            return False
        parameter = re.compile(r"^<(?:(?:[a-zA-Z_][a-zA-Z0-9_]*):)?[a-zA-Z_][a-zA-Z0-9_]*>$")
        return all(
            a == b or parameter.fullmatch(a) or parameter.fullmatch(b)
            for a, b in zip(left_parts, right_parts, strict=True)
        )
