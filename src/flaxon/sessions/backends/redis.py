from __future__ import annotations

import json
from typing import Any

from flaxon.sessions.session import Session


class RedisBackend:
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "flaxon:session",
        decode_responses: bool = True,
    ) -> None:
        self.redis_url = redis_url
        self.prefix = prefix
        self.decode_responses = decode_responses
        self._client = None

    async def connect(self) -> None:
        try:
            import redis.asyncio as redis
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=self.decode_responses,
            )
        except ImportError as exc:
            raise RuntimeError("redis is required. Install with: pip install redis") from exc

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    def _key(self, session_id: str) -> str:
        return f"{self.prefix}:{session_id}"

    async def save(self, session: Session) -> None:
        data = {
            "id": session.id,
            "data": session.to_dict(),
            "ttl": session.ttl,
            "created_at": session.created_at,
        }
        await self._client.setex(
            self._key(session.id),
            session.ttl,
            json.dumps(data, default=str, ensure_ascii=False),
        )

    async def get(self, session_id: str) -> Session | None:
        data = await self._client.get(self._key(session_id))
        if data is None:
            return None

        try:
            session_data = json.loads(data)
            return Session(
                session_id=session_data["id"],
                data=session_data["data"],
                ttl=session_data["ttl"],
                created_at=session_data["created_at"],
            )
        except (json.JSONDecodeError, KeyError):
            return None

    async def delete(self, session_id: str) -> None:
        await self._client.delete(self._key(session_id))

    async def clear(self) -> None:
        pattern = f"{self.prefix}:*"
        keys = await self._client.keys(pattern)
        if keys:
            await self._client.delete(*keys)

    async def exists(self, session_id: str) -> bool:
        return bool(await self._client.exists(self._key(session_id)))

    async def touch(self, session_id: str, ttl: int) -> None:
        await self._client.expire(self._key(session_id), ttl)

    def get_stats(self) -> dict[str, Any]:
        return {
            "backend": "redis",
            "url": self.redis_url,
        }
