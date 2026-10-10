from __future__ import annotations

import hashlib
import hmac
from typing import Any

from .cookie import CookieSession
from .session import Session


class SessionManager:
    """Session manager implementation for the sessions subsystem."""

    def __init__(  # noqa: PLR0917 - preserve existing positional API
        self,
        backend: Any,
        secret_key: str,
        cookie_name: str = "session",
        ttl: int = 86400,
        cookie_path: str = "/",
        cookie_domain: str | None = None,
        cookie_secure: bool = True,
        cookie_httponly: bool = True,
        cookie_samesite: str = "lax",
    ) -> None:
        self.backend = backend
        self.secret_key = secret_key.encode()
        self.cookie_name = cookie_name
        self.ttl = ttl
        self.cookie_path = cookie_path
        self.cookie_domain = cookie_domain
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite

    def _sign(self, data: str) -> str:
        return hmac.new(self.secret_key, data.encode(), hashlib.sha256).hexdigest()

    def _verify(self, data: str, signature: str) -> bool:
        expected = self._sign(data)
        return hmac.compare_digest(expected, signature)

    async def create(self, data: dict[str, Any] | None = None) -> Session:
        """Create a new entry from the supplied values."""
        session = Session(data=data or {}, ttl=self.ttl)
        await self.backend.save(session)
        return session

    async def get(self, session_id: str) -> Session | None:
        """Retrieve the requested value using this object's configured behavior."""
        return await self.backend.get(session_id)

    async def get_or_create(self, session_id: str | None = None) -> Session:
        """Retrieve an existing entry or create one from the supplied defaults."""
        if session_id:
            session = await self.get(session_id)
            if session and not session.is_expired():
                return session

        return await self.create()

    async def save(self, session: Session) -> None:
        """Persist the supplied value using the configured storage."""
        await self.backend.save(session)

    async def delete(self, session_id: str) -> None:
        """Delete the specified entry from the configured store."""
        await self.backend.delete(session_id)

    async def regenerate(self, session: Session) -> Session:
        """Perform the regenerate operation for session manager."""
        old_id = session.id
        session.regenerate()
        await self.backend.delete(old_id)
        await self.backend.save(session)
        return session

    def create_cookie(self, session: Session) -> str:
        """Create the cookie."""
        cookie = CookieSession(
            name=self.cookie_name,
            value=f"{session.id}:{self._sign(session.id)}",
            max_age=session.ttl,
            path=self.cookie_path,
            domain=self.cookie_domain,
            secure=self.cookie_secure,
            httponly=self.cookie_httponly,
            samesite=self.cookie_samesite,
        )
        return cookie.to_header()

    def delete_cookie(self) -> str:
        """Delete the cookie."""
        cookie = CookieSession(
            name=self.cookie_name,
            value="",
            max_age=0,
            path=self.cookie_path,
            domain=self.cookie_domain,
            secure=self.cookie_secure,
            httponly=self.cookie_httponly,
            samesite=self.cookie_samesite,
        )
        return cookie.to_header()

    def parse_cookie(self, cookie_value: str) -> tuple[str, bool] | None:
        """Parse the cookie."""
        try:
            if ":" not in cookie_value:
                return None

            session_id, signature = cookie_value.split(":", 1)

            if not self._verify(session_id, signature):
                return None

            return session_id, True

        except ValueError:
            return None

    async def get_from_cookie(self, cookie_value: str) -> Session | None:
        """Return the from cookie."""
        parsed = self.parse_cookie(cookie_value)
        if not parsed:
            return None

        session_id, _ = parsed
        return await self.get(session_id)
