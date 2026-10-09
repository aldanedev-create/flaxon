from __future__ import annotations

import hashlib
import hmac
import json
import time

from flaxon.sessions.session import Session


class SignedCookieBackend:
    def __init__(self, secret_key: str, ttl: int = 86400) -> None:
        self.secret_key = secret_key.encode()
        self.ttl = ttl

    def _sign(self, data: str) -> str:
        return hmac.new(self.secret_key, data.encode(), hashlib.sha256).hexdigest()

    def _verify(self, data: str, signature: str) -> bool:
        expected = self._sign(data)
        return hmac.compare_digest(expected, signature)

    def encode_session(self, session: Session) -> str:
        data = json.dumps({
            "id": session.id,
            "data": session.to_dict(),
            "ttl": session.ttl,
            "created_at": session.created_at,
        }, default=str, ensure_ascii=False)
        signature = self._sign(data)
        return f"{data}.{signature}"

    def decode_session(self, cookie_value: str) -> Session | None:
        try:
            parts = cookie_value.rsplit(".", 1)
            if len(parts) != 2:
                return None

            data, signature = parts

            if not self._verify(data, signature):
                return None

            session_data = json.loads(data)

            if time.time() - session_data.get("created_at", 0) > session_data.get("ttl", self.ttl):
                return None

            return Session(
                session_id=session_data["id"],
                data=session_data["data"],
                ttl=session_data["ttl"],
                created_at=session_data["created_at"],
            )

        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            return None

    async def save(self, session: Session) -> None:
        pass

    async def get(self, session_id: str) -> Session | None:
        return None

    async def delete(self, session_id: str) -> None:
        pass

    async def clear(self) -> None:
        pass

    async def exists(self, session_id: str) -> bool:
        return False
