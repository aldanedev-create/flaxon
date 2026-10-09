from __future__ import annotations

import functools
import hashlib
import secrets
from collections.abc import Callable
from typing import Any

from flaxon.exceptions import Unauthorized
from flaxon.http import Request


class APIKeyManager:
    def __init__(self) -> None:
        self._keys: dict[str, dict[str, Any]] = {}

    def generate_key(self, prefix: str = "flx") -> tuple[str, str]:
        key = f"{prefix}_{secrets.token_urlsafe(32)}"
        hashed = hashlib.sha256(key.encode()).hexdigest()
        return key, hashed

    def register(self, key: str, metadata: dict[str, Any] | None = None) -> None:
        hashed = hashlib.sha256(key.encode()).hexdigest()
        self._keys[hashed] = {
            "created": __import__("time").time(),
            "metadata": metadata or {},
            "active": True,
        }

    def register_hashed(self, hashed: str, metadata: dict[str, Any] | None = None) -> None:
        self._keys[hashed] = {
            "created": __import__("time").time(),
            "metadata": metadata or {},
            "active": True,
        }

    def validate(self, key: str) -> dict[str, Any] | None:
        hashed = hashlib.sha256(key.encode()).hexdigest()
        record = self._keys.get(hashed)
        if record and record.get("active", True):
            return record
        return None

    def revoke(self, key: str) -> None:
        hashed = hashlib.sha256(key.encode()).hexdigest()
        if hashed in self._keys:
            self._keys[hashed]["active"] = False

    def revoke_hashed(self, hashed: str) -> None:
        if hashed in self._keys:
            self._keys[hashed]["active"] = False

    def delete(self, key: str) -> None:
        hashed = hashlib.sha256(key.encode()).hexdigest()
        self._keys.pop(hashed, None)

    def list_keys(self) -> list[dict[str, Any]]:
        result = []
        for hashed, record in self._keys.items():
            result.append({
                "hashed": hashed[:8] + "...",
                "created": record["created"],
                "metadata": record["metadata"],
                "active": record.get("active", True),
            })
        return result


def api_key_required(header_name: str = "x-api-key") -> Callable:
    def decorator(func: Callable) -> Callable:
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
                raise Unauthorized("API key required")

            api_key = request.headers.get(header_name)
            if not api_key:
                raise Unauthorized("API key missing")

            manager = getattr(request.app, "api_key_manager", None)
            if manager is None:
                raise Unauthorized("API key manager not configured")

            record = manager.validate(api_key)
            if record is None:
                raise Unauthorized("Invalid API key")

            request.api_key_metadata = record.get("metadata", {})
            result = func(*args, **kwargs)
            if hasattr(result, "__await__"):
                return await result
            return result
        return wrapper
    return decorator
