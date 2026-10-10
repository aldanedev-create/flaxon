"""
Application state management.

This module provides a simple state container for storing application-wide
data such as database connections, caches, and service instances.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


class State(SimpleNamespace):
    """
    Application state container.

    This is a SimpleNamespace that can hold arbitrary attributes.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize state with optional values."""
        super().__init__(**kwargs)

    def get(self, name: str, default: Any = None) -> Any:
        """Get a state attribute with a default value."""
        return getattr(self, name, default)

    def setdefault(self, name: str, default: Any) -> Any:
        """Set a state attribute if it doesn't already exist."""
        if not hasattr(self, name):
            setattr(self, name, default)
        return getattr(self, name)

    def update(self, **kwargs: Any) -> None:
        """Update state with multiple attributes."""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        """Convert state to a dictionary."""
        return dict(self.__dict__)

    def clear(self) -> None:
        """Clear all state attributes."""
        for key in list(self.__dict__.keys()):
            delattr(self, key)

    def __repr__(self) -> str:
        """Return a string representation of the state."""
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"State({attrs})"

    def __len__(self) -> int:
        """Return the number of state attributes."""
        return len(self.__dict__)

    def __contains__(self, name: str) -> bool:
        """Check if a state attribute exists."""
        return hasattr(self, name)
