from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from flaxon.exceptions import Forbidden
from flaxon.security._request import endpoint_request


class Role:
    """Role implementation for the security subsystem."""

    def __init__(
        self,
        name: str,
        permissions: list[str] | None = None,
        description: str | None = None,
        parent: Role | None = None,
    ) -> None:
        self.name = name
        self.permissions = permissions or []
        self.description = description or name
        self.parent = parent

    def add_permission(self, permission: str) -> None:
        """Add the permission."""
        if permission not in self.permissions:
            self.permissions.append(permission)

    def remove_permission(self, permission: str) -> None:
        """Remove the permission."""
        if permission in self.permissions:
            self.permissions.remove(permission)

    def has_permission(self, permission: str) -> bool:
        """Return whether the requested permission is available."""
        if permission in self.permissions:
            return True
        if self.parent:
            return self.parent.has_permission(permission)
        return False

    def get_all_permissions(self) -> set[str]:
        """Return the all permissions."""
        perms = set(self.permissions)
        if self.parent:
            perms.update(self.parent.get_all_permissions())
        return perms

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Role(name={self.name}, permissions={self.permissions})"


class RoleRegistry:
    """Role registry implementation for the security subsystem."""

    _instance: RoleRegistry | None = None

    def __new__(cls) -> RoleRegistry:
        """Allocate an instance with the requested configuration."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._roles = {}
        return cls._instance

    def register(self, role: Role) -> None:
        """Perform the register operation for role registry."""
        self._roles[role.name] = role

    def get(self, name: str) -> Role | None:
        """Retrieve the requested value using this object's configured behavior."""
        return self._roles.get(name)

    def list_all(self) -> list[Role]:
        """List the all."""
        return list(self._roles.values())

    def exists(self, name: str) -> bool:
        """Return whether the requested entry exists."""
        return name in self._roles

    def clear(self) -> None:
        """Remove the stored entries."""
        self._roles.clear()


def register_role(
    name: str,
    permissions: list[str] | None = None,
    description: str | None = None,
    parent: Role | None = None,
) -> Role:
    """Register the role."""
    role = Role(name, permissions, description, parent)
    RoleRegistry().register(role)
    return role


def role_required(role: str | Role) -> Callable:
    """Protect a callable with a role requirement."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = endpoint_request(args, kwargs)

            user = getattr(request, "user", None) if request else None
            role_name = role.name if isinstance(role, Role) else role

            if user is None:
                raise Forbidden("Authentication required")

            if not user.has_role(role_name):
                raise Forbidden(f"Role '{role_name}' required")

            result = func(*args, **kwargs)
            if hasattr(result, "__await__"):
                return await result
            return result

        return wrapper

    return decorator


class RoleChecker:
    """Role checker implementation for the security subsystem."""

    def __init__(self, user: Any) -> None:
        self.user = user

    def has(self, role: str | Role) -> bool:
        """Perform the has operation for role checker."""
        role_name = role.name if isinstance(role, Role) else role
        return self.user.has_role(role_name) if self.user else False

    def require(self, role: str | Role) -> None:
        """Perform the require operation for role checker."""
        if not self.has(role):
            role_name = role.name if isinstance(role, Role) else role
            raise Forbidden(f"Role '{role_name}' required")

    def require_any(self, *roles: str | Role) -> None:
        """Require the any."""
        for role in roles:
            if self.has(role):
                return
        names = [r.name if isinstance(r, Role) else r for r in roles]
        raise Forbidden(f"One of roles required: {', '.join(names)}")

    def require_all(self, *roles: str | Role) -> None:
        """Require the all."""
        for role in roles:
            self.require(role)
