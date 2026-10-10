from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from flaxon.exceptions import Forbidden
from flaxon.security._request import endpoint_request


class Permission:
    """Permission implementation for the security subsystem."""

    def __init__(self, name: str, description: str | None = None) -> None:
        self.name = name
        self.description = description or name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Permission(name={self.name}, description={self.description})"


class PermissionRegistry:
    """Permission registry implementation for the security subsystem."""

    _instance: PermissionRegistry | None = None

    def __new__(cls) -> PermissionRegistry:
        """Allocate an instance with the requested configuration."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._permissions = {}
        return cls._instance

    def register(self, permission: Permission) -> None:
        """Perform the register operation for permission registry."""
        self._permissions[permission.name] = permission

    def get(self, name: str) -> Permission | None:
        """Retrieve the requested value using this object's configured behavior."""
        return self._permissions.get(name)

    def list_all(self) -> list[Permission]:
        """List the all."""
        return list(self._permissions.values())

    def exists(self, name: str) -> bool:
        """Return whether the requested entry exists."""
        return name in self._permissions

    def clear(self) -> None:
        """Remove the stored entries."""
        self._permissions.clear()


def register_permission(name: str, description: str | None = None) -> Permission:
    """Register the permission."""
    permission = Permission(name, description)
    PermissionRegistry().register(permission)
    return permission


def permission_required(permission: str | Permission) -> Callable:
    """Protect a callable with a permission requirement."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = endpoint_request(args, kwargs)

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
    """Permission checker implementation for the security subsystem."""

    def __init__(self, user: Any) -> None:
        self.user = user

    def has(self, permission: str | Permission) -> bool:
        """Perform the has operation for permission checker."""
        perm_name = permission.name if isinstance(permission, Permission) else permission
        return self.user.has_permission(perm_name) if self.user else False

    def require(self, permission: str | Permission) -> None:
        """Perform the require operation for permission checker."""
        if not self.has(permission):
            perm_name = permission.name if isinstance(permission, Permission) else permission
            raise Forbidden(f"Permission '{perm_name}' required")

    def require_any(self, *permissions: str | Permission) -> None:
        """Require the any."""
        for permission in permissions:
            if self.has(permission):
                return
        names = [p.name if isinstance(p, Permission) else p for p in permissions]
        raise Forbidden(f"One of permissions required: {', '.join(names)}")

    def require_all(self, *permissions: str | Permission) -> None:
        """Require the all."""
        for permission in permissions:
            self.require(permission)
