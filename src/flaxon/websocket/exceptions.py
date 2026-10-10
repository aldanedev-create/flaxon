from __future__ import annotations

from flaxon.exceptions import FlaxonError


class WebSocketError(FlaxonError):
    """Report a web socket failure."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class WebSocketConnectionError(WebSocketError):
    """Report a web socket connection failure."""

    def __init__(self, message: str = "WebSocket connection failed") -> None:
        super().__init__(message)


class WebSocketHandshakeError(WebSocketError):
    """Report a web socket handshake failure."""

    def __init__(self, message: str = "WebSocket handshake failed") -> None:
        super().__init__(message)


class WebSocketProtocolError(WebSocketError):
    """Report a web socket protocol failure."""

    def __init__(self, message: str = "WebSocket protocol error") -> None:
        super().__init__(message)


class WebSocketMessageError(WebSocketError):
    """Report a web socket message failure."""

    def __init__(self, message: str = "WebSocket message error") -> None:
        super().__init__(message)


class WebSocketTimeoutError(WebSocketError):
    """Report a web socket timeout failure."""

    def __init__(self, message: str = "WebSocket timeout") -> None:
        super().__init__(message)


class WebSocketRoomError(WebSocketError):
    """Report a web socket room failure."""

    def __init__(self, message: str = "WebSocket room error") -> None:
        super().__init__(message)


class WebSocketBroadcastError(WebSocketError):
    """Report a web socket broadcast failure."""

    def __init__(self, message: str = "WebSocket broadcast error") -> None:
        super().__init__(message)


class WebSocketAuthenticationError(WebSocketError):
    """Report a web socket authentication failure."""

    def __init__(self, message: str = "WebSocket authentication failed") -> None:
        super().__init__(message)
