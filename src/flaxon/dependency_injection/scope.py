from __future__ import annotations

import contextvars
from typing import Any


class Scope:
    """Manage named dependency scopes and context-local values."""

    _current_scope: contextvars.ContextVar[str] = contextvars.ContextVar("di_scope", default="global")
    _scope_data: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
        "di_scope_data", default=None
    )

    def __init__(self, name: str = "global") -> None:
        self.name = name

    def __enter__(self) -> Scope:
        self._token = Scope._current_scope.set(self.name)
        self._data_token = Scope._scope_data.set({})
        return self

    def __exit__(self, *args: Any) -> None:
        Scope._current_scope.reset(self._token)
        Scope._scope_data.reset(self._data_token)

    @classmethod
    def get_current(cls) -> str:
        """Return the dependency scope selected in the active context."""
        return cls._current_scope.get()

    @classmethod
    def set_data(cls, key: str, value: Any) -> None:
        """Set a scope-local value without mutating inherited context data."""
        data = dict(cls._scope_data.get() or {})
        data[key] = value
        cls._scope_data.set(data)

    @classmethod
    def get_data(cls, key: str, default: Any = None) -> Any:
        """Read a scope-local value or return the supplied fallback."""
        return (cls._scope_data.get() or {}).get(key, default)

    @classmethod
    def clear_data(cls) -> None:
        """Replace the active scope data with an empty dictionary."""
        cls._scope_data.set({})


class ScopedContainer:
    """Store local instances while falling back to a parent container."""

    def __init__(self, parent_container: Any, name: str) -> None:
        self.parent = parent_container
        self.name = name
        self._instances: dict[str, Any] = {}

    def get(self, name: str) -> Any:
        """Return a local instance or resolve the name through the parent container."""
        if name in self._instances:
            return self._instances[name]
        return self.parent.get(name)

    def set(self, name: str, value: Any) -> None:
        """Store an instance directly in this scoped container."""
        self._instances[name] = value

    def clear(self) -> None:
        """Remove providers or local instances owned by this container."""
        self._instances.clear()


class ScopeManager:
    """Create named scopes and track the selected scope."""

    def __init__(self) -> None:
        self._scopes: dict[str, Scope] = {}
        self._active_scope: str = "global"

    def create_scope(self, name: str) -> None:
        """Register a scope with the supplied name."""
        self._scopes[name] = Scope(name)

    def enter_scope(self, name: str) -> Scope:
        """Select and return a named scope, creating it when necessary."""
        scope = self._scopes.get(name)
        if scope is None:
            scope = Scope(name)
            self._scopes[name] = scope
        self._active_scope = name
        return scope

    def exit_scope(self) -> None:
        """Select the global scope as this manager's active scope."""
        self._active_scope = "global"

    def get_active_scope(self) -> str:
        """Return the name selected by this scope manager."""
        return self._active_scope

    def get_scope(self, name: str) -> Scope | None:
        """Return a registered scope, or None if its name is unknown."""
        return self._scopes.get(name)

    def remove_scope(self, name: str) -> None:
        """Remove a named scope registration."""
        self._scopes.pop(name, None)

    def clear(self) -> None:
        """Remove providers or local instances owned by this container."""
        self._scopes.clear()
        self._active_scope = "global"
