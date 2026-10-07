from __future__ import annotations

import base64
import functools
import hashlib
import hmac
import json
import time
from typing import Any

from flaxon.exceptions import Unauthorized
from flaxon.http import Request


class JWT:
    def __init__(self, secret_key: str, algorithm: str = "HS256") -> None:
        self.secret_key = secret_key.encode()
        self.algorithm = algorithm

    def _sign(self, data: str) -> str:
        return hmac.new(self.secret_key, data.encode(), hashlib.sha256).hexdigest()

    def _base64_encode(self, data: str) -> str:
        return base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")

    def _base64_decode(self, data: str) -> str:
        padding = "=" * (4 - len(data) % 4)
        return base64.urlsafe_b64decode(data + padding).decode()

    def encode(self, payload: dict[str, Any], expires_in: int = 3600) -> str:
        header = {"alg": self.algorithm, "typ": "JWT"}
        payload_data = {
            **payload,
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in,
        }
        header_encoded = self._base64_encode(json.dumps(header))
        payload_encoded = self._base64_encode(json.dumps(payload_data))
        signature = self._sign(f"{header_encoded}.{payload_encoded}")
        return f"{header_encoded}.{payload_encoded}.{signature}"

    def decode(self, token: str) -> dict[str, Any]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise Unauthorized("Invalid token format")

            header_encoded, payload_encoded, signature = parts

            expected = self._sign(f"{header_encoded}.{payload_encoded}")
            if not hmac.compare_digest(expected, signature):
                raise Unauthorized("Invalid token signature")

            payload_data = json.loads(self._base64_decode(payload_encoded))
            if payload_data.get("exp", 0) < time.time():
                raise Unauthorized("Token has expired")

            return payload_data
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            raise Unauthorized("Invalid token") from exc


def jwt_required(func: Any) -> Any:
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        if request is None:
            for arg in kwargs.values():
                if isinstance(arg, Request):
                    request = arg
                    break

        if request is None:
            raise Unauthorized("Authentication required")

        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise Unauthorized("Missing or invalid authorization header")

        token = auth_header[7:]
        jwt = getattr(request.app, "jwt", None)
        if jwt is None:
            raise Unauthorized("JWT not configured")

        payload = jwt.decode(token)
        request.user = payload

        result = func(*args, **kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result
    return wrapper


def create_jwt_token(user_id: str | int, secret_key: str, data: dict[str, Any] | None = None, expires_in: int = 3600) -> str:
    """
    Create a signed JWT for a user.

    secret_key must be your application's own secret (e.g. app.config.get_secret_key()).
    There is intentionally no default secret here -- a shared, guessable default
    would let anyone forge valid tokens for any user.
    """
    payload = {"user_id": str(user_id), **(data or {})}
    jwt = JWT(secret_key)
    return jwt.encode(payload, expires_in=expires_in)
