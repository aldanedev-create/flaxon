from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from flaxon.exceptions import Forbidden
from flaxon.http import Request


class Permission:
    def __init__(self, name: str, description: str | None = None) -> None:
        self.name = name
        self.description = description or name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Permission(name={self.name}, description={self.description})"


class PermissionRegistry:
    _instance: PermissionRegistry | None = None

    def __new__(cls) -> PermissionRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._permissions = {}
        return cls._instance

    def register(self, permission: Permission) -> None:
        self._permissions[permission.name] = permission

    def get(self, name: str) -> Permission | None:
        return self._permissions.get(name)

    def list_all(self) -> list[Permission]:
        return list(self._permissions.values())

    def exists(self, name: str) -> bool:
        return name in self._permissions

    def clear(self) -> None:
        self._permissions.clear()


def register_permission(name: str, description: str | None = None) -> Permission:
    permission = Permission(name, description)
    PermissionRegistry().register(permission)
    return permission


def permission_required(permission: str | Permission) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
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

            user = getattr(request, "user", None) if request else None
            perm_name = permission.name if isinstance(permission, Permission) else permission

            if user is None:
                raise Forbidden("Authentication required")

            if not user.has_permission(perm_name):
                raise Forbidden(f"Permission '{perm_name}' required")

            result = func(*args, **kwargs)
            if hasattr(result, "__await__"):
                return await result
            return result
        return wrapper
    return decorator


class PermissionChecker:
    def __init__(self, user: Any) -> None:
        self.user = user

    def has(self, permission: str | Permission) -> bool:
        perm_name = permission.name if isinstance(permission, Permission) else permission
        return self.user.has_permission(perm_name) if self.user else False

    def require(self, permission: str | Permission) -> None:
        if not self.has(permission):
            perm_name = permission.name if isinstance(permission, Permission) else permission
            raise Forbidden(f"Permission '{perm_name}' required")

    def require_any(self, *permissions: str | Permission) -> None:
        for permission in permissions:
            if self.has(permission):
                return
        names = [p.name if isinstance(p, Permission) else p for p in permissions]
        raise Forbidden(f"One of permissions required: {', '.join(names)}")

    def require_all(self, *permissions: str | Permission) -> None:
        for permission in permissions:
            self.require(permission)
