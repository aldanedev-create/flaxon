from __future__ import annotations

import hashlib
import hmac
import json
import math
import time
import uuid
from typing import Any

from flaxon.http import Cookies, Request, Response


class Session:
    """Session implementation for the security subsystem."""

    def __init__(  # noqa: PLR0917 - preserve existing positional API
        self,
        session_id: str,
        data: dict[str, Any] | None = None,
        ttl: int = 86400,
        cookie_name: str = "session",
        cookie_path: str = "/",
        cookie_domain: str | None = None,
        cookie_secure: bool = False,
        cookie_httponly: bool = True,
        cookie_samesite: str = "lax",
    ) -> None:
        self.session_id = session_id
        self._data = data or {}
        self.ttl = ttl
        self.cookie_name = cookie_name
        self.cookie_path = cookie_path
        self.cookie_domain = cookie_domain
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite
        self._dirty = False
        self._created = time.time()

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._dirty = True

    def __delitem__(self, key: str) -> None:
        del self._data[key]
        self._dirty = True

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve the requested value using this object's configured behavior."""
        return self._data.get(key, default)

    def setdefault(self, key: str, default: Any) -> Any:
        """Perform the setdefault operation for session."""
        if key not in self._data:
            self._data[key] = default
            self._dirty = True
        return self._data[key]

    def update(self, data: dict[str, Any]) -> None:
        """Apply the supplied changes to the requested entry."""
        self._data.update(data)
        self._dirty = True

    def clear(self) -> None:
        """Remove the stored entries."""
        self._data.clear()
        self._dirty = True

    def pop(self, key: str, default: Any = None) -> Any:
        """Perform the pop operation for session."""
        value = self._data.pop(key, default)
        self._dirty = True
        return value

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the current value."""
        return dict(self._data)

    def is_expired(self) -> bool:
        """Return whether expired holds for the current value."""
        return time.time() - self._created > self.ttl

    def is_dirty(self) -> bool:
        """Return whether dirty holds for the current value."""
        return self._dirty

    def mark_clean(self) -> None:
        """Mark the clean."""
        self._dirty = False


class SessionManager:
    """Session manager implementation for the security subsystem."""

    def __init__(  # noqa: PLR0917 - preserve existing positional API
        self,
        secret_key: str,
        cookie_name: str = "session",
        ttl: int = 86400,
        cookie_path: str = "/",
        cookie_domain: str | None = None,
        cookie_secure: bool = False,
        cookie_httponly: bool = True,
        cookie_samesite: str = "lax",
    ) -> None:
        self.secret_key = secret_key.encode()
        self.cookie_name = cookie_name
        self.ttl = ttl
        self.cookie_path = cookie_path
        self.cookie_domain = cookie_domain
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite
        self._sessions: dict[str, dict[str, Any]] = {}

    def _sign(self, data: str) -> str:
        return hmac.new(self.secret_key, data.encode(), hashlib.sha256).hexdigest()

    def _verify(self, data: str, signature: str) -> bool:
        expected = self._sign(data)
        return hmac.compare_digest(expected, signature)

    def _encode(self, session: Session) -> str:
        data = json.dumps({
            "id": session.session_id,
            "data": session._data,
            "created": session._created,
            "ttl": session.ttl,
        })
        signature = self._sign(data)
        return f"{data}.{signature}"

    def _decode(self, cookie: str) -> tuple[dict[str, Any], bool] | None:
        try:
            parts = cookie.rsplit(".", 1)
            if len(parts) != 2:
                return None
            data, signature = parts
            if not self._verify(data, signature):
                return None
            payload = json.loads(data)
            if not self._valid_cookie_payload(payload):
                return None
            return payload, True
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    def _valid_cookie_payload(self, payload: Any) -> bool:
        if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
            return False
        if not isinstance(payload.get("data", {}), dict):
            return False
        created = payload.get("created")
        ttl = payload.get("ttl")
        if isinstance(created, bool) or not isinstance(created, (int, float)) or not math.isfinite(created):
            return False
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or not math.isfinite(ttl) or ttl <= 0:
            return False
        now = time.time()
        return not (created > now or created + min(ttl, self.ttl) <= now)

    def _generate_session_id(self) -> str:
        return uuid.uuid4().hex[:32]

    def get_session(self, request: Request) -> Session:
        """Return the session."""
        cookies = request.cookies
        session = None

        if self.cookie_name in cookies:
            decoded = self._decode(cookies[self.cookie_name])
            if decoded:
                data, valid = decoded
                if valid:
                    session = Session(
                        session_id=data["id"],
                        data=data.get("data", {}),
                        ttl=data.get("ttl", self.ttl),
                        cookie_name=self.cookie_name,
                        cookie_path=self.cookie_path,
                        cookie_domain=self.cookie_domain,
                        cookie_secure=self.cookie_secure,
                        cookie_httponly=self.cookie_httponly,
                        cookie_samesite=self.cookie_samesite,
                    )
                    session._created = data.get("created", time.time())

        if session is None:
            session = Session(
                session_id=self._generate_session_id(),
                ttl=self.ttl,
                cookie_name=self.cookie_name,
                cookie_path=self.cookie_path,
                cookie_domain=self.cookie_domain,
                cookie_secure=self.cookie_secure,
                cookie_httponly=self.cookie_httponly,
                cookie_samesite=self.cookie_samesite,
            )

        return session

    def save_session(self, session: Session, response: Response) -> None:
        """Save the session."""
        if session.is_dirty():
            cookie_value = self._encode(session)
            cookies = Cookies()
            cookies.set(
                self.cookie_name,
                cookie_value,
                max_age=session.ttl,
                path=session.cookie_path,
                domain=session.cookie_domain,
                secure=session.cookie_secure,
                httponly=session.cookie_httponly,
                samesite=session.cookie_samesite,
            )
            for header in cookies.to_headers():
                response.headers.setdefault("set-cookie", header)
