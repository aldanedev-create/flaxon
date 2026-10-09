from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class Signal(StrEnum):
    """Lifecycle events emitted by background tasks."""

    PRE_RUN = "pre_run"
    POST_RUN = "post_run"
    ON_SUCCESS = "on_success"
    ON_FAILURE = "on_failure"
    ON_RETRY = "on_retry"
    ON_CANCELLED = "on_cancelled"
    ON_TIMEOUT = "on_timeout"


class SignalHandler:
    """Dispatch task notifications without stopping subsequent listeners."""

    def __init__(self) -> None:
        self._handlers: dict[Signal, list[Callable[..., Any]]] = {signal: [] for signal in Signal}

    def connect(self, signal: Signal, handler: Callable[..., Any]) -> None:
        """Subscribe a listener to the selected signal."""
        if signal not in self._handlers:
            self._handlers[signal] = []
        self._handlers[signal].append(handler)

    def disconnect(self, signal: Signal, handler: Callable[..., Any]) -> None:
        """Remove a previously subscribed listener."""
        if signal in self._handlers and handler in self._handlers[signal]:
            self._handlers[signal].remove(handler)

    async def emit(self, signal: Signal, *args: Any, **kwargs: Any) -> None:
        """Notify the current listeners, logging failures and continuing."""
        if signal not in self._handlers:
            return

        for handler in tuple(self._handlers[signal]):
            try:
                result = handler(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                # Application callbacks are an isolation boundary. Cancellation
                # still propagates, and failures remain visible to operators.
                logger.exception("Task signal listener failed (signal=%s)", signal.value)


class SignalManager:
    """Keep signal subscriptions isolated by task identifier."""

    def __init__(self) -> None:
        self._handlers: dict[str, SignalHandler] = {}

    def get_handler(self, task_id: str) -> SignalHandler:
        """Return the subscription collection for a task."""
        if task_id not in self._handlers:
            self._handlers[task_id] = SignalHandler()
        return self._handlers[task_id]

    def remove_handler(self, task_id: str) -> None:
        """Discard all subscriptions for a task."""
        self._handlers.pop(task_id, None)

    def clear(self) -> None:
        """Discard subscriptions for every task."""
        self._handlers.clear()

    def connect(self, task_id: str, signal: Signal, handler: Callable[..., Any]) -> None:
        """Subscribe a listener to the selected signal."""
        handler_obj = self.get_handler(task_id)
        handler_obj.connect(signal, handler)

    def disconnect(self, task_id: str, signal: Signal, handler: Callable[..., Any]) -> None:
        """Remove a previously subscribed listener."""
        handler_obj = self.get_handler(task_id)
        handler_obj.disconnect(signal, handler)

    async def emit(self, task_id: str, signal: Signal, *args: Any, **kwargs: Any) -> None:
        """Notify the current listeners, logging failures and continuing."""
        handler_obj = self.get_handler(task_id)
        await handler_obj.emit(signal, *args, **kwargs)


_default_signal_manager = SignalManager()


def connect_signal(task_id: str, signal: Signal, handler: Callable[..., Any]) -> None:
    """Subscribe a listener through the default task signal manager."""
    _default_signal_manager.connect(task_id, signal, handler)


def disconnect_signal(task_id: str, signal: Signal, handler: Callable[..., Any]) -> None:
    """Remove a listener from the default task signal manager."""
    _default_signal_manager.disconnect(task_id, signal, handler)


async def emit_signal(task_id: str, signal: Signal, *args: Any, **kwargs: Any) -> None:
    """Emit a notification through the default task signal manager."""
    await _default_signal_manager.emit(task_id, signal, *args, **kwargs)
