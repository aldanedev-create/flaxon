from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Any

from flaxon.sessions.session import Session


class MemoryBackend:
    """Provide memory storage for sessions operations."""

    def __init__(self) -> None:
        self._sessions: dict[str, tuple[Session, float]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the configured service."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop the configured service."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

    async def save(self, session: Session) -> None:
        """Persist the supplied value using the configured storage."""
        async with self._lock:
            self._sessions[session.id] = (session, time.time() + session.ttl)

    async def get(self, session_id: str) -> Session | None:
        """Retrieve the requested value using this object's configured behavior."""
        async with self._lock:
            if session_id not in self._sessions:
                return None

            session, expires = self._sessions[session_id]
            if time.time() > expires:
                del self._sessions[session_id]
                return None

            return session

    async def delete(self, session_id: str) -> None:
        """Delete the specified entry from the configured store."""
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def clear(self) -> None:
        """Remove the stored entries."""
        async with self._lock:
            self._sessions.clear()

    async def exists(self, session_id: str) -> bool:
        """Return whether the requested entry exists."""
        async with self._lock:
            if session_id not in self._sessions:
                return False

            _, expires = self._sessions[session_id]
            if time.time() > expires:
                del self._sessions[session_id]
                return False

            return True

    async def _cleanup_loop(self) -> None:
        while self._running:
            await asyncio.sleep(60)
            current_time = time.time()
            async with self._lock:
                to_remove = []
                for session_id, (_, expires) in self._sessions.items():
                    if current_time > expires:
                        to_remove.append(session_id)
                for session_id in to_remove:
                    self._sessions.pop(session_id, None)

    def get_stats(self) -> dict[str, Any]:
        """Return the stats."""
        return {
            "total_sessions": len(self._sessions),
        }
