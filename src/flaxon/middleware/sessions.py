"""
Session middleware for Flaxon.

This module provides middleware for handling HTTP sessions.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

from .base import Middleware


class Session:
    """HTTP session."""

    def __init__(
        self,
        session_id: str,
        data: dict[str, Any] | None = None,
        *,
        ttl: int = 86400,
        secure: bool = True,
        httponly: bool = True,
        samesite: str = "lax",
    ) -> None:
        self.session_id = session_id
        self._data = data or {}
        self._dirty = False
        self.ttl = ttl
        self.secure = secure
        self.httponly = httponly
        self.samesite = samesite
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
        return self._data.get(key, default)

    def setdefault(self, key: str, default: Any) -> Any:
        if key not in self._data:
            self._data[key] = default
            self._dirty = True
        return self._data[key]

    def update(self, data: dict[str, Any]) -> None:
        self._data.update(data)
        self._dirty = True

    def clear(self) -> None:
        self._data.clear()
        self._dirty = True

    def pop(self, key: str, default: Any = None) -> Any:
        value = self._data.pop(key, default)
        self._dirty = True
        return value

    def keys(self) -> list[str]:
        return list(self._data.keys())

    def values(self) -> list[Any]:
        return list(self._data.values())

    def items(self) -> list[tuple[str, Any]]:
        return list(self._data.items())

    def is_expired(self) -> bool:
        return time.time() - self._created > self.ttl

    def is_dirty(self) -> bool:
        return self._dirty

    def mark_clean(self) -> None:
        self._dirty = False

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)


class SessionMiddleware(Middleware):
    """Session middleware."""

    def __init__(
        self,
        app: Any,
        secret_key: str,
        cookie_name: str = "session",
        ttl: int = 86400,
        secure: bool = True,
        httponly: bool = True,
        samesite: str = "lax",
    ) -> None:
        super().__init__(app)
        self.secret_key = secret_key.encode()
        self.cookie_name = cookie_name
        self.ttl = ttl
        self.secure = secure
        self.httponly = httponly
        self.samesite = samesite

    def _sign(self, data: str) -> str:
        return hmac.new(self.secret_key, data.encode(), hashlib.sha256).hexdigest()

    def _verify(self, data: str, signature: str) -> bool:
        expected = self._sign(data)
        return hmac.compare_digest(expected, signature)

    def _encode_session(self, session: Session) -> str:
        data = json.dumps({
            "id": session.session_id,
            "data": session._data,
            "created": session._created,
            "ttl": session.ttl,
        })
        signature = self._sign(data)
        return f"{data}.{signature}"

    def _decode_session(self, cookie: str) -> tuple[dict[str, Any], bool] | None:
        try:
            parts = cookie.split(".", 1)
            if len(parts) != 2:
                return None
            data, signature = parts
            if not self._verify(data, signature):
                return None
            return json.loads(data), True
        except (json.JSONDecodeError, ValueError):
            return None

    def _get_session_id(self) -> str:
        import uuid
        return uuid.uuid4().hex[:32]

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        cookies = self._parse_cookies(scope)
        session: Session | None = None

        if self.cookie_name in cookies:
            decoded = self._decode_session(cookies[self.cookie_name])
            if decoded:
                data, valid = decoded
                if valid and data.get("id"):
                    session = Session(
                        session_id=data["id"],
                        data=data.get("data", {}),
                        ttl=data.get("ttl", self.ttl),
                        secure=self.secure,
                        httponly=self.httponly,
                        samesite=self.samesite,
                    )
                    session._created = data.get("created", time.time())

        if session is None:
            session = Session(
                session_id=self._get_session_id(),
                ttl=self.ttl,
                secure=self.secure,
                httponly=self.httponly,
                samesite=self.samesite,
            )

        scope["session"] = session

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                if session.is_dirty():
                    cookie_value = self._encode_session(session)
                    headers = list(message.get("headers", []))
                    cookie_header = (
                        f"{self.cookie_name}={cookie_value}; "
                        f"Path=/; Max-Age={session.ttl}; "
                        f"SameSite={session.samesite.capitalize()}"
                    )
                    if session.secure:
                        cookie_header += "; Secure"
                    if session.httponly:
                        cookie_header += "; HttpOnly"
                    headers.append((b"set-cookie", cookie_header.encode("latin-1")))
                    message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _parse_cookies(self, scope: dict[str, Any]) -> dict[str, str]:
        cookies: dict[str, str] = {}
        for key, value in scope.get("headers", []):
            if key.lower() == b"cookie":
                for cookie in value.decode("latin-1").split(";"):
                    cookie = cookie.strip()
                    if "=" in cookie:
                        k, v = cookie.split("=", 1)
                        cookies[k.strip()] = v.strip()
        return cookies
