from __future__ import annotations

from flaxon.exceptions import FlaxonError


class EventError(FlaxonError):
    """Report a event failure."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class EventNotFoundError(EventError):
    """Report a event not found failure."""

    def __init__(self, message: str = "Event not found") -> None:
        """Perform the   init   operation for event not found error."""
        super().__init__(message)


class EventHandlerError(EventError):
    """Report a event handler failure."""

    def __init__(self, message: str = "Event handler error") -> None:
        super().__init__(message)


class EventSubscriptionError(EventError):
    """Report a event subscription failure."""

    def __init__(self, message: str = "Event subscription error") -> None:
        super().__init__(message)


class EventDispatcherError(EventError):
    """Report a event dispatcher failure."""

    def __init__(self, message: str = "Event dispatcher error") -> None:
        super().__init__(message)
