from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import Any

from flaxon.exceptions import Unauthorized
from flaxon.http import Request

from .jwt import JWT


class User:
    def __init__(
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
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def to_dict(self) -> dict[str, Any]:
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
        return cls(
            id=data["id"],
            username=data.get("username"),
            email=data.get("email"),
            roles=data.get("roles", []),
            permissions=data.get("permissions", []),
            metadata=data.get("metadata", {}),
        )


class AuthenticationBackend(ABC):
    @abstractmethod
    async def authenticate(self, request: Request) -> User | None:
        pass

    @abstractmethod
    async def create_token(self, user: User, expires_in: int | None = None) -> str:
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> User | None:
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> None:
        pass


class JWTBackend(AuthenticationBackend):
    _instances: list[JWTBackend] = []

    def __init__(self, secret_key: str, algorithm: str = "HS256", **options: Any) -> None:
        self.jwt = JWT(secret_key, algorithm, **options)
        self.secret_key = secret_key.encode()
        self.algorithm = algorithm
        self._revoked: dict[str, float] = {}
        self._instances.append(self)

    async def authenticate(self, request: Request) -> User | None:
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None

        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]
        return await self.validate_token(token)

    async def create_token(self, user: User, expires_in: int | None = None) -> str:
        return self.jwt.encode(user.to_dict(), expires_in=3600 if expires_in is None else expires_in)

    async def validate_token(self, token: str) -> User | None:
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
    _instances: list[SessionBackend] = []

    def __init__(self, session_store: dict[str, dict[str, Any]] | None = None) -> None:
        self.sessions: dict[str, dict[str, Any]] = session_store or {}
        self._instances.append(self)

    async def authenticate(self, request: Request) -> User | None:
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
        import uuid
        expires_in = expires_in or 86400
        session_id = uuid.uuid4().hex[:32]
        self.sessions[session_id] = {
            "user": user.to_dict(),
            "created": int(time.time()),
            "expires": int(time.time()) + expires_in,
        }
        return session_id

    async def validate_token(self, token: str) -> User | None:
        session = self.sessions.get(token)
        if not session:
            return None
        if session.get("expires", 0) < time.time():
            del self.sessions[token]
            return None
        return User.from_dict(session.get("user", {}))

    async def revoke_token(self, token: str) -> None:
        self.sessions.pop(token, None)


class AuthenticationMiddleware:
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
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        for exclude in self.exclude_paths:
            if path.startswith(exclude):
                await self.app(scope, receive, send)
                return

        from flaxon.http import Request
        request = Request(scope, receive, None)

        try:
            user = await self.backend.authenticate(request)
            if user:
                scope["user"] = user
                request.user = user
        except Unauthorized:
            scope["user"] = None

        await self.app(scope, receive, send)


async def authenticate(request: Request, backend: AuthenticationBackend) -> User | None:
    return await backend.authenticate(request)


async def get_current_user(request: Request) -> User | None:
    return getattr(request, "user", None)


def login_required(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        if request is None:
            for arg in kwargs.values():
                if isinstance(arg, Request):
                    request = arg
                    break
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

        if hasattr(func, "__call__"):
            result = func(*args, **kwargs)
            if hasattr(result, "__await__"):
                return await result
            return result
        return func(*args, **kwargs)
    return wrapper
