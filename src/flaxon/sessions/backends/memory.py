from __future__ import annotations

import asyncio
import time
from typing import Any

from flaxon.sessions.session import Session


class MemoryBackend:
    def __init__(self) -> None:
        self._sessions: dict[str, tuple[Session, float]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def save(self, session: Session) -> None:
        async with self._lock:
            self._sessions[session.id] = (session, time.time() + session.ttl)

    async def get(self, session_id: str) -> Session | None:
        async with self._lock:
            if session_id not in self._sessions:
                return None

            session, expires = self._sessions[session_id]
            if time.time() > expires:
                del self._sessions[session_id]
                return None

            return session

    async def delete(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def clear(self) -> None:
        async with self._lock:
            self._sessions.clear()

    async def exists(self, session_id: str) -> bool:
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
        return {
            "total_sessions": len(self._sessions),
        }
