"""Durable services used by the Admin production integration.

The services deliberately depend on the small AdminStore contract so projects
can replace it with their own database-backed repository.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, Callable


@dataclass
class DurableJob:
    id: str
    name: str
    payload: dict[str, Any]
    status: str = "queued"
    attempts: int = 0
    max_attempts: int = 3
    error: str | None = None
    run_after: float = 0.0
    created_at: float = 0.0
    updated_at: float = 0.0
    history: list[dict[str, Any]] | None = None
    worker_id: str | None = None
    lease_until: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class DurableJobStore:
    """Persistent job queue with retry history and idempotent completion."""

    def __init__(self, store: Any, namespace: str = "admin_jobs") -> None:
        self.store = store
        self.namespace = namespace
        self.worker_id = secrets.token_urlsafe(10)
        self.lease_seconds = 300.0
        self._fallback_lock = threading.RLock()

    def _save(self, jobs: dict[str, Any]) -> None:
        self.store.set(self.namespace, "jobs", jobs)

    def _mutate(self, callback: Callable[[dict[str, Any]], Any]) -> Any:
        """Update the queue under the store's atomic JSON-key primitive.

        ``AdminStore.mutate`` uses a database write lock, so separate worker
        processes cannot claim the same job. Custom stores can implement the
        same method; the locked read/write fallback remains useful for simple
        single-process stores.
        """

        if hasattr(self.store, "mutate"):
            return self.store.mutate(self.namespace, "jobs", callback, {})
        with self._fallback_lock:
            jobs = self.store.get(self.namespace, "jobs", {}) or {}
            result = callback(jobs)
            self._save(jobs)
            return result

    @staticmethod
    def _event(raw: dict[str, Any], event: str, **details: Any) -> None:
        history = raw.get("history") or []
        raw["history"] = history
        history.append({"event": event, "at": time.time(), **details})
        del history[:-100]

    def list(self, status: str | None = None) -> list[DurableJob]:
        jobs = [DurableJob(**item) for item in (self.store.get(self.namespace, "jobs", {}) or {}).values()]
        return [job for job in jobs if status is None or job.status == status]

    def enqueue(
        self,
        name: str,
        payload: dict[str, Any],
        *,
        max_attempts: int = 3,
        run_after: float = 0.0,
        job_id: str | None = None,
    ) -> DurableJob:
        now = time.time()
        job = DurableJob(job_id or secrets.token_urlsafe(16), name, payload, max_attempts=max(1, max_attempts), run_after=run_after, created_at=now, updated_at=now)
        def add(jobs: dict[str, Any]) -> dict[str, Any]:
            existing = jobs.get(job.id)
            if existing is not None:
                return existing
            raw = job.to_dict()
            self._event(raw, "enqueued", name=name)
            jobs[job.id] = raw
            return raw

        return DurableJob(**self._mutate(add))

    def claim_due(self, limit: int = 10) -> list[DurableJob]:
        now = time.time()
        def claim(jobs: dict[str, Any]) -> list[dict[str, Any]]:
            claimed: list[dict[str, Any]] = []
            for raw in sorted(jobs.values(), key=lambda value: value.get("created_at", 0)):
                if len(claimed) >= max(1, limit):
                    break
                # Recover a job whose worker died without completing it.
                if raw.get("status") == "running" and raw.get("lease_until", 0) <= now:
                    raw["status"] = "queued"
                    self._event(raw, "lease_expired")
                if raw.get("status") != "queued" or raw.get("run_after", 0) > now:
                    continue
                raw["status"] = "running"
                raw["attempts"] = int(raw.get("attempts", 0)) + 1
                raw["worker_id"] = self.worker_id
                raw["lease_until"] = now + self.lease_seconds
                raw["updated_at"] = now
                self._event(raw, "claimed", attempt=raw["attempts"], worker_id=self.worker_id)
                claimed.append(dict(raw))
            return claimed

        return [DurableJob(**raw) for raw in self._mutate(claim)]

    def complete(self, job_id: str) -> None:
        def finish(jobs: dict[str, Any]) -> None:
            raw = jobs.get(job_id)
            if raw is None or raw.get("status") == "completed":
                return
            raw.update(status="completed", error=None, lease_until=0.0, updated_at=time.time())
            self._event(raw, "completed", worker_id=self.worker_id)

        self._mutate(finish)

    def fail(self, job_id: str, error: str, retry_delay: float = 5.0) -> None:
        def fail_job(jobs: dict[str, Any]) -> None:
            raw = jobs.get(job_id)
            if raw is None or raw.get("status") == "completed":
                return
            now = time.time()
            attempts = int(raw.get("attempts", 0))
            retrying = attempts < int(raw.get("max_attempts", 3))
            raw.update(
                status="queued" if retrying else "failed",
                error=error,
                run_after=now + retry_delay * max(1, attempts) if retrying else 0.0,
                lease_until=0.0,
                updated_at=now,
            )
            self._event(raw, "retry_scheduled" if retrying else "failed", error=error, attempt=attempts)

        self._mutate(fail_job)

    def retry_failed(self, job_id: str, *, delay: float = 0.0) -> DurableJob:
        """Move a failed job back to the queue for an operator retry."""

        def retry(jobs: dict[str, Any]) -> dict[str, Any]:
            raw = jobs.get(job_id)
            if raw is None:
                raise KeyError(job_id)
            raw.update(status="queued", run_after=time.time() + max(0.0, delay), error=None, lease_until=0.0, updated_at=time.time())
            self._event(raw, "manual_retry")
            return raw

        return DurableJob(**self._mutate(retry))

    def history(self, job_id: str | None = None) -> list[dict[str, Any]]:
        jobs = self.list()
        events = [event | {"job_id": job.id, "name": job.name} for job in jobs for event in (job.history or [])]
        if job_id is not None:
            events = [event for event in events if event["job_id"] == job_id]
        return sorted(events, key=lambda event: event.get("at", 0), reverse=True)


class DurableJobWorker:
    def __init__(self, jobs: DurableJobStore) -> None:
        self.jobs = jobs
        self.handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def register(self, name: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        self.handlers[name] = handler

    async def run_once(self, limit: int = 10) -> list[DurableJob]:
        completed: list[DurableJob] = []
        for job in self.jobs.claim_due(limit):
            try:
                handler = self.handlers[job.name]
                result = handler(job.payload)
                if isawaitable(result):
                    await result
                self.jobs.complete(job.id)
                completed.append(job)
            except Exception as exc:  # noqa: BLE001
                self.jobs.fail(job.id, str(exc))
        return completed

    async def run_forever(self, poll_interval: float = 0.5, stop_event: Any | None = None) -> None:
        """Run registered handlers until an optional async stop event is set."""

        while stop_event is None or not stop_event.is_set():
            await self.run_once()
            await asyncio.sleep(max(0.05, poll_interval))


class ImmutableAuditLog:
    """Append-only hash chained audit log with verification and retention."""

    def __init__(self, store: Any, namespace: str = "audit") -> None:
        self.store = store
        self.namespace = namespace

    def append(self, action: str, actor: str, details: dict[str, Any], *, ip: str | None = None, user_agent: str | None = None) -> dict[str, Any]:
        created: dict[str, Any] = {}

        def append_entry(current: list[dict[str, Any]]) -> list[dict[str, Any]]:
            entries = current if isinstance(current, list) else []
            anchors = self.store.get(self.namespace, "anchors", []) or []
            previous_hash = entries[-1]["hash"] if entries else (anchors[-1].get("hash") if anchors else "0" * 64)
            entry = {"id": secrets.token_hex(12), "action": action, "actor": actor, "details": details, "ip": ip, "user_agent": user_agent, "created_at": time.time(), "previous_hash": previous_hash}
            entry["hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
            created.update(entry)
            entries.append(entry)
            return entries

        if hasattr(self.store, "mutate"):
            self.store.mutate(self.namespace, "entries", append_entry, [])
        else:
            entries = append_entry(self.store.get(self.namespace, "entries", []) or [])
            self.store.set(self.namespace, "entries", entries)
        return created

    def verify(self) -> bool:
        anchors = self.store.get(self.namespace, "anchors", []) or []
        previous = anchors[-1].get("hash") if anchors else "0" * 64
        for entry in self.store.get(self.namespace, "entries", []) or []:
            candidate = dict(entry)
            digest = candidate.pop("hash", "")
            if candidate.get("previous_hash") != previous or not hmac.compare_digest(hashlib.sha256(json.dumps(candidate, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest(), digest):
                return False
            previous = digest
        return True

    def prune(self, before: float) -> int:
        entries = self.store.get(self.namespace, "entries", []) or []
        kept = [entry for entry in entries if entry.get("created_at", 0) >= before]
        if len(kept) != len(entries):
            # Keep the retained hashes untouched. The removed prefix becomes
            # a verifiable retention anchor instead of silently rewriting the
            # audit history.
            anchors = self.store.get(self.namespace, "anchors", []) or []
            anchor_hash = kept[0].get("previous_hash") if kept else entries[-1].get("hash")
            anchors.append({"hash": anchor_hash, "created_at": time.time(), "before": before})
            self.store.set(self.namespace, "anchors", anchors[-100:])
            self.store.set(self.namespace, "entries", kept)
        return len(entries) - len(kept)


class NotificationService:
    def __init__(self, store: Any, namespace: str = "notifications", max_messages: int = 5000) -> None:
        self.store = store
        self.namespace = namespace
        self.max_messages = max(100, max_messages)
        self.channel_senders: dict[str, Callable[[str, dict[str, Any]], Any]] = {}

    def register_channel(self, channel: str, sender: Callable[[str, dict[str, Any]], Any]) -> None:
        self.channel_senders[str(channel)] = sender

    def set_preferences(self, username: str, preferences: dict[str, bool]) -> None:
        values = self.store.get(self.namespace, "preferences", {}) or {}
        values[username] = {str(key): bool(value) for key, value in preferences.items()}
        self.store.set(self.namespace, "preferences", values)

    def preferences(self, username: str) -> dict[str, bool]:
        return (self.store.get(self.namespace, "preferences", {}) or {}).get(username, {})

    def list(self, username: str, *, unread_only: bool = False, limit: int = 20) -> list[dict[str, Any]]:
        messages = [item for item in self.store.get(self.namespace, "messages", []) or [] if item.get("username") == username]
        if unread_only:
            messages = [item for item in messages if not item.get("read")]
        return list(reversed(messages[-max(1, min(limit, self.max_messages)) :]))

    def mark_read(self, username: str, ids: list[str] | None = None, *, all_messages: bool = False) -> int:
        selected = {str(item) for item in (ids or [])}
        messages = self.store.get(self.namespace, "messages", []) or []
        changed = 0
        for message in messages:
            if message.get("username") != username or (not all_messages and message.get("id") not in selected):
                continue
            if not message.get("read"):
                message["read"] = True
                message["read_at"] = time.time()
                changed += 1
        self.store.set(self.namespace, "messages", messages[-self.max_messages :])
        return changed

    def _store_message(self, username: str, channel: str, payload: dict[str, Any]) -> dict[str, Any]:
        message = {"id": secrets.token_urlsafe(12), "username": username, "channel": channel, "payload": payload, "created_at": time.time(), "read": False, "delivery_status": "stored"}
        messages = self.store.get(self.namespace, "messages", []) or []
        messages.append(message)
        self.store.set(self.namespace, "messages", messages[-self.max_messages :])
        return message

    def _set_delivery(self, message_id: str, status: str, error: str | None = None) -> None:
        messages = self.store.get(self.namespace, "messages", []) or []
        for message in messages:
            if message.get("id") == message_id:
                message["delivery_status"] = status
                if error:
                    message["delivery_error"] = error
        self.store.set(self.namespace, "messages", messages[-self.max_messages :])

    async def _deliver(self, channel: str, message: dict[str, Any], sender: Callable[[str, dict[str, Any]], Any]) -> None:
        try:
            result = sender(channel, message)
            if isawaitable(result):
                await result
            message["delivery_status"] = "delivered"
            self._set_delivery(message["id"], "delivered")
        except Exception as exc:  # noqa: BLE001
            message["delivery_status"] = "failed"
            message["delivery_error"] = str(exc)
            self._set_delivery(message["id"], "failed", str(exc))

    def publish(self, username: str, channel: str, payload: dict[str, Any], sender: Callable[[str, dict[str, Any]], Any] | None = None) -> dict[str, Any]:
        preferences = self.preferences(username)
        if preferences.get(channel) is False:
            return {"delivered": False, "reason": "disabled"}
        message = self._store_message(username, channel, payload)
        callback = sender or self.channel_senders.get(channel)
        if callback is None:
            return {"delivered": True, "message": message}
        result = callback(channel, message)
        if isawaitable(result):
            async def finish() -> None:
                try:
                    await result
                    message["delivery_status"] = "delivered"
                    self._set_delivery(message["id"], "delivered")
                except Exception as exc:  # noqa: BLE001
                    message["delivery_status"] = "failed"
                    message["delivery_error"] = str(exc)
                    self._set_delivery(message["id"], "failed", str(exc))

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(finish())
            else:
                loop.create_task(finish())
                message["delivery_status"] = "pending"
                return {"delivered": True, "pending": True, "message": message}
        self._set_delivery(message["id"], "delivered")
        return {"delivered": True, "message": message}

    async def publish_async(self, username: str, channel: str, payload: dict[str, Any], sender: Callable[[str, dict[str, Any]], Any] | None = None) -> dict[str, Any]:
        preferences = self.preferences(username)
        if preferences.get(channel) is False:
            return {"delivered": False, "reason": "disabled"}
        message = self._store_message(username, channel, payload)
        callback = sender or self.channel_senders.get(channel)
        if callback is None:
            return {"delivered": True, "message": message}
        await self._deliver(channel, message, callback)
        return {"delivered": message.get("delivery_status") == "delivered", "message": message}


class ResumableUploadStore:
    """Chunk store that survives restarts and validates the final digest."""

    def __init__(self, store: Any, namespace: str = "uploads") -> None:
        self.store = store
        self.namespace = namespace

    def create(
        self,
        filename: str,
        total_size: int,
        sha256: str | None = None,
        *,
        content_type: str = "application/octet-stream",
        expires_in: int = 86400,
    ) -> str:
        if total_size < 0:
            raise ValueError("Upload size cannot be negative")
        upload_id = secrets.token_urlsafe(16)
        uploads = self.store.get(self.namespace, "sessions", {}) or {}
        now = time.time()
        uploads[upload_id] = {"filename": filename, "total_size": total_size, "sha256": sha256, "content_type": content_type, "chunks": {}, "next_offset": 0, "created_at": now, "expires_at": now + max(60, expires_in)}
        self.store.set(self.namespace, "sessions", uploads)
        return upload_id

    def status(self, upload_id: str) -> dict[str, Any]:
        uploads = self.store.get(self.namespace, "sessions", {}) or {}
        session = uploads.get(upload_id)
        if session is None or session.get("expires_at", 0) < time.time():
            raise ValueError("Upload session not found")
        return {"upload_id": upload_id, "filename": session["filename"], "content_type": session.get("content_type", "application/octet-stream"), "total_size": int(session["total_size"]), "offset": int(session.get("next_offset", 0)), "complete": int(session.get("next_offset", 0)) == int(session["total_size"]), "expires_at": session.get("expires_at")}

    def put_chunk(self, upload_id: str, offset: int, data: bytes) -> None:
        uploads = self.store.get(self.namespace, "sessions", {}) or {}
        session = uploads.get(upload_id)
        if session is None or session.get("expires_at", 0) < time.time() or offset < 0 or offset + len(data) > int(session["total_size"]):
            raise ValueError("Invalid upload chunk")
        expected = int(session.get("next_offset", 0))
        if offset != expected:
            raise ValueError(f"Upload offset mismatch; expected {expected}")
        session["chunks"][str(offset)] = base64.b64encode(data).decode("ascii")
        session["next_offset"] = expected + len(data)
        self.store.set(self.namespace, "sessions", uploads)

    def finalize(self, upload_id: str) -> tuple[str, bytes]:
        uploads = self.store.get(self.namespace, "sessions", {}) or {}
        session = uploads.get(upload_id)
        if session is None or session.get("expires_at", 0) < time.time():
            raise ValueError("Upload session not found")
        parts = [base64.b64decode(value) for _, value in sorted(session["chunks"].items(), key=lambda item: int(item[0]))]
        data = b"".join(parts)
        if len(data) != int(session["total_size"]):
            raise ValueError("Upload is incomplete")
        digest = hashlib.sha256(data).hexdigest()
        if session.get("sha256") and not hmac.compare_digest(digest, session["sha256"]):
            raise ValueError("Upload digest mismatch")
        del uploads[upload_id]
        self.store.set(self.namespace, "sessions", uploads)
        return session["filename"], data

    def cleanup_expired(self, now: float | None = None) -> int:
        current = now or time.time()
        uploads = self.store.get(self.namespace, "sessions", {}) or {}
        expired = [key for key, session in uploads.items() if session.get("expires_at", 0) < current]
        for key in expired:
            del uploads[key]
        if expired:
            self.store.set(self.namespace, "sessions", uploads)
        return len(expired)


class WebAuthnService:
    """Adapter boundary for a real WebAuthn implementation.

    Pass a provider backed by ``webauthn``/``py-webauthn``. The service stores
    credential metadata but never accepts a client assertion by itself.
    """

    def __init__(self, store: Any, provider: Any | None = None, namespace: str = "webauthn") -> None:
        self.store = store
        self.provider = provider
        self.namespace = namespace

    def begin_registration(self, username: str, **kwargs: Any) -> Any:
        if self.provider is None:
            raise RuntimeError("A WebAuthn provider is required")
        return self.provider.begin_registration(username, **kwargs)

    def finish_registration(self, username: str, response: Any) -> Any:
        if self.provider is None:
            raise RuntimeError("A WebAuthn provider is required")
        credential = self.provider.finish_registration(username, response)
        values = self.store.get(self.namespace, username, []) or []
        values.append(credential)
        self.store.set(self.namespace, username, values)
        return credential

    def begin_authentication(self, username: str) -> Any:
        if self.provider is None:
            raise RuntimeError("A WebAuthn provider is required")
        return self.provider.begin_authentication(username, self.store.get(self.namespace, username, []) or [])

    def finish_authentication(self, username: str, response: Any) -> bool:
        if self.provider is None:
            raise RuntimeError("A WebAuthn provider is required")
        return bool(self.provider.finish_authentication(username, response, self.store.get(self.namespace, username, []) or []))
