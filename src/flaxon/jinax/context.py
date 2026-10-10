from __future__ import annotations

from typing import Any


class Context:
    """Context implementation for the jinax subsystem."""

    def __init__(self, parent: Context | None = None) -> None:
        self.parent = parent
        self._data: dict[str, Any] = {}

    def get(self, name: str, default: Any = None) -> Any:
        """Retrieve the requested value using this object's configured behavior."""
        if name in self._data:
            return self._data[name]
        if self.parent:
            return self.parent.get(name, default)
        return default

    def set(self, name: str, value: Any) -> None:
        """Store the supplied value under its key."""
        self._data[name] = value

    def push(self) -> Context:
        """Perform the push operation for context."""
        return Context(self)

    def pop(self) -> Context | None:
        """Perform the pop operation for context."""
        return self.parent

    def update(self, data: dict[str, Any]) -> None:
        """Apply the supplied changes to the requested entry."""
        self._data.update(data)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        result = {}
        if self.parent:
            result.update(self.parent.to_dict())
        result.update(self._data)
        return result

    def __getitem__(self, name: str) -> Any:
        return self.get(name)

    def __setitem__(self, name: str, value: Any) -> None:
        self.set(name, value)

    def __contains__(self, name: str) -> bool:
        return name in self._data or (self.parent and name in self.parent)

    def __repr__(self) -> str:
        """Perform the   repr   operation for context."""
        return f"Context({self.to_dict()})"


class ContextStack:
    """Context stack implementation for the jinax subsystem."""

    def __init__(self) -> None:
        self._stack: list[Context] = [Context()]

    def push(self) -> None:
        """Perform the push operation for context stack."""
        self._stack.append(Context(self.current()))

    def pop(self) -> Context | None:
        """Perform the pop operation for context stack."""
        if len(self._stack) > 1:
            return self._stack.pop()
        return None

    def current(self) -> Context:
        """Perform the current operation for context stack."""
        return self._stack[-1]

    def get(self, name: str, default: Any = None) -> Any:
        """Retrieve the requested value using this object's configured behavior."""
        return self.current().get(name, default)

    def set(self, name: str, value: Any) -> None:
        """Store the supplied value under its key."""
        self.current().set(name, value)

    def update(self, data: dict[str, Any]) -> None:
        """Apply the supplied changes to the requested entry."""
        self.current().update(data)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        return self.current().to_dict()

    def __getitem__(self, name: str) -> Any:
        return self.current().get(name)

    def __setitem__(self, name: str, value: Any) -> None:
        self.current().set(name, value)
