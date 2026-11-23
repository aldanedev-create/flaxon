"""Session-bound impersonation ("login as").

Safety rules, all enforced server-side:

* Disabled by default (``AdminConfig(allow_impersonation=True)`` to enable).
* The actor needs the explicit ``admin.impersonate`` permission.
* Superusers can never be impersonated — that would be privilege escalation.
* You cannot impersonate yourself.
* The state is bound to the actor's session token; logging out or switching
  sessions ends it. Every start and stop is written to the audit log.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from flaxon._imports import import_attribute

__all__ = ["ImpersonationManager"]

_NAMESPACE = "impersonation"
SUPERUSER = "admin.superuser"


def _token(request: Any) -> str | None:
    cookies = getattr(request, "cookies", None) or {}
    token = cookies.get("session_id") if hasattr(cookies, "get") else None
    return str(token) if token else None


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _is_superuser(record: dict[str, Any]) -> bool:
    return SUPERUSER in set(record.get("permissions") or ())


class ImpersonationManager:
    """Start, inspect and stop impersonation for the current session."""

    def __init__(self, dashboard: Any, *, enabled: bool = False) -> None:
        self.dashboard = dashboard
        self.enabled = bool(enabled)
        self._memory: dict[str, dict[str, Any]] = {}

    def _read(self, token: str) -> dict[str, Any] | None:
        store = self.dashboard.store
        if store is None:
            return self._memory.get(_digest(token))
        stored: Any = store.get(_NAMESPACE, _digest(token), None)
        return stored if isinstance(stored, dict) else None

    def _write(self, token: str, value: dict[str, Any] | None) -> None:
        store = self.dashboard.store
        if store is None:
            if value is None:
                self._memory.pop(_digest(token), None)
            else:
                self._memory[_digest(token)] = value
            return
        if value is None:
            store.delete(_NAMESPACE, _digest(token))
        else:
            store.set(_NAMESPACE, _digest(token), value)

    def active(self, request: Any) -> dict[str, Any] | None:
        """Return the active impersonation record for this session, if any."""
        token = _token(request)
        if not token:
            return None
        return self._read(token)

    def clear(self, request: Any) -> None:
        """Drop impersonation state for this session without auditing."""
        token = _token(request)
        if token:
            self._write(token, None)

    async def start(self, request: Any, username: str) -> dict[str, Any]:
        """Begin impersonating ``username`` for the current session."""
        forbidden = import_attribute("flaxon.exceptions", "Forbidden")
        bad_request = import_attribute("flaxon.exceptions", "BadRequest")
        not_found = import_attribute("flaxon.exceptions", "NotFound")

        if not self.enabled:
            raise forbidden("Impersonation is disabled")
        token = _token(request)
        actor = getattr(request, "user", None)
        if not token or actor is None:
            raise forbidden("Impersonation requires an authenticated session")
        if not await self.dashboard.auth.has_permission_async(actor, "admin.impersonate"):
            raise forbidden("You are not allowed to impersonate users")

        record = self.dashboard.auth.users.get(str(username))
        if record is None:
            raise not_found("Unknown user")
        if str(username) == getattr(actor, "username", None):
            raise bad_request("You cannot impersonate yourself")
        if _is_superuser(record):
            raise forbidden("Superusers cannot be impersonated")

        entry = {
            "actor": actor.username,
            "target": str(username),
            "started_at": time.time(),
        }
        self._write(token, entry)
        self.dashboard.record_activity("impersonation_started", "users", request, record_id=str(username))
        return entry

    async def stop(self, request: Any) -> dict[str, Any] | None:
        """End impersonation for this session and audit the stop."""
        entry = self.active(request)
        if entry is None:
            return None
        self.clear(request)
        actor = self.dashboard.auth.user(entry["actor"])
        original = getattr(request, "user", None)
        if actor is not None:
            request.user = actor
        try:
            self.dashboard.record_activity(
                "impersonation_stopped", "users", request, record_id=str(entry.get("target", ""))
            )
        finally:
            if actor is not None:
                request.user = original
        return entry
