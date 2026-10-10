from __future__ import annotations

import hashlib
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import Any, ClassVar

from flaxon._imports import import_attribute
from flaxon.exceptions import Unauthorized
from flaxon.http import Request
from flaxon.security._request import endpoint_request

from .jwt import JWT


class User:
    """User implementation for the security subsystem."""

    def __init__(  # noqa: PLR0917 - preserve existing positional API
        self,
        id: str | int,
        username: str | None = None,
        email: str | None = None,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = id
        self.username = username
        self.email = email
        self.roles = roles or []
        self.permissions = permissions or []
        self.metadata = metadata or {}

    def has_role(self, role: str) -> bool:
        """Return whether the requested role is available."""
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Return whether the requested permission is available."""
        return permission in self.permissions

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "permissions": self.permissions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User:
        """Construct an instance from its dictionary representation."""
        return cls(
            id=data["id"],
            username=data.get("username"),
            email=data.get("email"),
            roles=data.get("roles", []),
            permissions=data.get("permissions", []),
            metadata=data.get("metadata", {}),
        )


class AuthenticationBackend(ABC):
    """Provide authentication storage for flaxon operations."""

    @abstractmethod
    async def authenticate(self, request: Request) -> User | None:
        """Resolve a user or identity using the configured authentication backend."""
        pass

    @abstractmethod
    async def create_token(self, user: User, expires_in: int | None = None) -> str:
        """Create the token."""
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> User | None:
        """Validate the token."""
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> None:
        """Revoke the token."""
        pass


class JWTBackend(AuthenticationBackend):
    """Provide jwt storage for flaxon operations."""

    _instances: ClassVar[list[JWTBackend]] = []

    def __init__(self, secret_key: str, algorithm: str = "HS256", **options: Any) -> None:
        self.jwt = JWT(secret_key, algorithm, **options)
        self.secret_key = secret_key.encode()
        self.algorithm = algorithm
        self._revoked: dict[str, float] = {}
        self._instances.append(self)

    async def authenticate(self, request: Request) -> User | None:
        """Resolve a user or identity using the configured authentication backend."""
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None

        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]
        return await self.validate_token(token)

    async def create_token(self, user: User, expires_in: int | None = None) -> str:
        """Create the token."""
        return self.jwt.encode(user.to_dict(), expires_in=3600 if expires_in is None else expires_in)

    async def validate_token(self, token: str) -> User | None:
        """Validate the token."""
        now = time.time()
        self._revoked = {key: expiry for key, expiry in self._revoked.items() if expiry > now}
        if hashlib.sha256(token.encode()).hexdigest() in self._revoked:
            return None
        try:
            return User.from_dict(self.jwt.decode(token))
        except (Unauthorized, KeyError, TypeError, ValueError):
            return None

    async def revoke_token(self, token: str) -> None:
        """Revoke locally until expiry; distributed deployments need a shared store."""
        try:
            payload = self.jwt.decode(token)
        except Unauthorized:
            return
        self._revoked[hashlib.sha256(token.encode()).hexdigest()] = float(payload["exp"]) + self.jwt.leeway


class SessionBackend(AuthenticationBackend):
    """Provide session storage for flaxon operations."""

    _instances: ClassVar[list[SessionBackend]] = []

    def __init__(self, session_store: dict[str, dict[str, Any]] | None = None) -> None:
        self.sessions: dict[str, dict[str, Any]] = session_store or {}
        self._instances.append(self)

    async def authenticate(self, request: Request) -> User | None:
        """Resolve a user or identity using the configured authentication backend."""
        session_id = request.cookies.get("session_id")
        if not session_id:
            return None

        session = self.sessions.get(session_id)
        if not session:
            return None

        if session.get("expires", 0) < time.time():
            del self.sessions[session_id]
            return None

        return User.from_dict(session.get("user", {}))

    async def create_token(self, user: User, expires_in: int | None = None) -> str:
        """Create the token."""
        expires_in = expires_in or 86400
        session_id = uuid.uuid4().hex[:32]
        self.sessions[session_id] = {
            "user": user.to_dict(),
            "created": int(time.time()),
            "expires": int(time.time()) + expires_in,
        }
        return session_id

    async def validate_token(self, token: str) -> User | None:
        """Validate the token."""
        session = self.sessions.get(token)
        if not session:
            return None
        if session.get("expires", 0) < time.time():
            del self.sessions[token]
            return None
        return User.from_dict(session.get("user", {}))

    async def revoke_token(self, token: str) -> None:
        """Revoke the token."""
        self.sessions.pop(token, None)


class AuthenticationMiddleware:
    """Authentication middleware implementation for the security subsystem."""

    def __init__(
        self,
        app: Any,
        backend: AuthenticationBackend,
        exclude_paths: list[str] | None = None,
    ) -> None:
        self.app = app
        self.backend = backend
        self.exclude_paths = exclude_paths or ["/health", "/auth/login", "/auth/register"]

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        for exclude in self.exclude_paths:
            if path.startswith(exclude):
                await self.app(scope, receive, send)
                return

        request_type = import_attribute("flaxon.http", "Request")

        request = request_type(scope, receive, None)

        try:
            user = await self.backend.authenticate(request)
            if user:
                scope["user"] = user
                request.user = user
        except Unauthorized:
            scope["user"] = None

        await self.app(scope, receive, send)


async def authenticate(request: Request, backend: AuthenticationBackend) -> User | None:
    """Resolve a user or identity using the configured authentication backend."""
    return await backend.authenticate(request)


async def get_current_user(request: Request) -> User | None:
    """Return the current user."""
    return getattr(request, "user", None)


def login_required(func: Callable) -> Callable:
    """Protect a callable with a login requirement."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request = endpoint_request(args, kwargs)
        if request is None:
            raise Unauthorized("Authentication required")

        user = getattr(request, "user", None)
        if user is None:
            authorization = request.headers.get("authorization", "")
            token = authorization.removeprefix("Bearer ").strip()
            if token:
                for backend in [*JWTBackend._instances, *SessionBackend._instances]:
                    user = await backend.validate_token(token)
                    if user is not None:
                        request.user = user
                        break
        if user is None:
            raise Unauthorized("Authentication required")

        if callable(func):
            result = func(*args, **kwargs)
            if hasattr(result, "__await__"):
                return await result
            return result
        return func(*args, **kwargs)

    return wrapper
