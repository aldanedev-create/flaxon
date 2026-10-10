from __future__ import annotations

from typing import Any


class Mock:
    """Mock implementation for the testing subsystem."""

    def __init__(self, name: str, return_value: Any = None) -> None:
        self.name = name
        self.return_value = return_value
        self._calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self._call_count = 0

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Handle the supplied call using this object's configured behavior."""
        self._calls.append((args, kwargs))
        self._call_count += 1

        if callable(self.return_value):
            return self.return_value(*args, **kwargs)
        return self.return_value

    def assert_called(self) -> None:
        """Assert the called."""
        assert self._call_count > 0, f"Mock '{self.name}' was not called"

    def assert_called_once(self) -> None:
        """Assert the called once."""
        assert self._call_count == 1, f"Mock '{self.name}' was called {self._call_count} times, expected 1"

    def assert_called_with(self, *args: Any, **kwargs: Any) -> None:
        """Assert the called with."""
        for call_args, call_kwargs in self._calls:
            if call_args == args and call_kwargs == kwargs:
                return
        raise AssertionError(f"Mock '{self.name}' was not called with args={args}, kwargs={kwargs}")

    def reset(self) -> None:
        """Perform the reset operation for mock."""
        self._calls.clear()
        self._call_count = 0


class MockRegistry:
    """Mock registry implementation for the testing subsystem."""

    def __init__(self) -> None:
        self._mocks: dict[str, Mock] = {}

    def register(self, name: str, return_value: Any = None) -> Mock:
        """Perform the register operation for mock registry."""
        mock = Mock(name, return_value)
        self._mocks[name] = mock
        return mock

    def get(self, name: str) -> Mock | None:
        """Retrieve the requested value using this object's configured behavior."""
        return self._mocks.get(name)

    def reset_all(self) -> None:
        """Reset the all."""
        for mock in self._mocks.values():
            mock.reset()

    def clear(self) -> None:
        """Remove the stored entries."""
        self._mocks.clear()
