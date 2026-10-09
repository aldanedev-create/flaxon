from __future__ import annotations

import functools
import time
from typing import Any, cast

import jwt as pyjwt

from flaxon.exceptions import Unauthorized
from flaxon.http import Request


class JWT:
    """Standard JWTs with a fixed algorithm and optional trusted key rotation."""

    def __init__(self, secret_key: str, algorithm: str = "HS256", *,
                 issuer: str | None = None, audience: str | None = None,
                 key_id: str | None = None,
                 verification_keys: dict[str, str] | None = None,
                 leeway: int = 0) -> None:
        if not secret_key:
            raise ValueError("JWT requires a nonempty secret key")
        if algorithm not in {"HS256", "HS384", "HS512"}:
            raise ValueError("JWT supports explicitly configured HS256, HS384, or HS512")
        if leeway < 0:
            raise ValueError("JWT leeway must be nonnegative")
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
        self.key_id = key_id
        self.verification_keys = dict(verification_keys or {})
        if any(not value for value in self.verification_keys.values()):
            raise ValueError("JWT verification keys must be nonempty")
        if key_id is not None:
            if key_id in self.verification_keys and self.verification_keys[key_id] != secret_key:
                raise ValueError("JWT active key ID must match the signing secret")
            self.verification_keys[key_id] = secret_key
        self.leeway = leeway

    def encode(self, payload: dict[str, Any], expires_in: int = 3600) -> str:
        """Issue a standard base64url JWT; configuration owns registered claims."""
        now = int(time.time())
        claims = {**payload, "iat": now, "exp": now + expires_in}
        if self.issuer is not None:
            claims["iss"] = self.issuer
        if self.audience is not None:
            claims["aud"] = self.audience
        headers = {"kid": self.key_id} if self.key_id is not None else None
        return cast(str, pyjwt.encode(claims, self.secret_key, algorithm=self.algorithm, headers=headers))

    def decode(self, token: str) -> dict[str, Any]:
        """Verify expiry, fixed algorithm, configured claims, and trusted key IDs."""
        try:
            header = pyjwt.get_unverified_header(token)
            if header.get("alg") != self.algorithm:
                raise Unauthorized("Invalid token algorithm")
            key = self.secret_key
            if "kid" in header:
                kid = header["kid"]
                if not isinstance(kid, str) or kid not in self.verification_keys:
                    raise Unauthorized("Unknown token key")
                key = self.verification_keys[kid]
            required = ["exp"]
            if self.issuer is not None:
                required.append("iss")
            if self.audience is not None:
                required.append("aud")
            return cast(dict[str, Any], pyjwt.decode(token, key, algorithms=[self.algorithm],
                                issuer=self.issuer, audience=self.audience,
                                leeway=self.leeway, options={"require": required}))
        except pyjwt.ExpiredSignatureError as exc:
            raise Unauthorized("Token has expired") from exc
        except (pyjwt.InvalidTokenError, ValueError, TypeError, OverflowError) as exc:
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
