from __future__ import annotations

import secrets
import time
import sqlite3
import json
import uuid
import base64
import hashlib
import hmac
from urllib.parse import quote
from dataclasses import dataclass, field
from typing import Any

from flaxon.exceptions import Forbidden, Unauthorized
from flaxon.http import Request, Response
from flaxon.security import PasswordHasher, PasswordValidator, SessionBackend, User
from flaxon.security import RateLimiter
from flaxon.security.rate_limit import DistributedRateLimiter


@dataclass
class AdminActivity:
    action: str
    resource: str
    record_id: str | None = None
    username: str = "system"
    timestamp: float = field(default_factory=time.time)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "resource": self.resource,
            "record_id": self.record_id,
            "username": self.username,
            "timestamp": self.timestamp,
            "details": self.details,
        }


class AdminAuth:
    """Small injectable admin auth service backed by Flaxon's token backend."""

    def __init__(self, users: list[dict[str, Any]] | None = None, backend: SessionBackend | None = None, store: Any | None = None, session_idle_timeout: int | None = None) -> None:
        self.backend = backend or SessionBackend()
        self.hasher = PasswordHasher()
        self.password_validator = PasswordValidator()
        self.users: dict[str, dict[str, Any]] = {}
        for raw in users or []:
            self.add_user(raw)
        self._login_failures: dict[str, list[float]] = {}
        self.role_permissions: dict[str, list[str]] = {}
        self._reset_tokens: dict[str, tuple[str, float]] = {}
        self._verification_tokens: dict[str, tuple[str, float]] = {}
        self.store = store
        self.session_idle_timeout = session_idle_timeout
        if self.store:
            self._reset_tokens = self.store.get("auth", "reset_tokens", {}) or {}
            self._verification_tokens = self.store.get("auth", "verification_tokens", {}) or {}
        # A fixed hash to verify against when a username doesn't exist, so
        # login response timing doesn't leak which usernames are valid
        # (CWE-208) -- without this, a nonexistent user returns almost
        # instantly while a real user with a wrong password takes as long
        # as a full PBKDF2 verification (tens of milliseconds), which is
        # trivially measurable and lets an attacker enumerate usernames.
        self._dummy_password_hash = self.hasher.hash(secrets.token_hex(32))

    def _persist_auth_tokens(self) -> None:
        if self.store:
            self.store.set("auth", "reset_tokens", self._reset_tokens)
            self.store.set("auth", "verification_tokens", self._verification_tokens)

    def add_user(self, raw: dict[str, Any]) -> dict[str, Any]:
        username = str(raw.get("username", "")).strip()
        if not username:
            raise ValueError("Admin users require a username")
        record = dict(raw)
        record["id"] = str(record.get("id") or secrets.token_hex(8))
        record["roles"] = list(record["roles"]) if "roles" in record else ["staff"]
        record["permissions"] = list(record["permissions"]) if "permissions" in record else ["admin:read", "admin:write", "admin:users", "admin:settings", "admin:media"]
        if record.get("password") and not record.get("password_hash"):
            password = str(record.pop("password"))
            errors = self.password_validator.validate(password)
            if errors:
                raise ValueError(errors[0])
            record["password_hash"] = self.hasher.hash(password)
        self.users[username] = record
        return record

    def public(self, record: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in record.items() if k not in {"password", "password_hash", "mfa_secret", "mfa_pending_secret", "mfa_pending_recovery_codes", "mfa_recovery_codes"}}

    def user(self, username: str) -> User | None:
        record = self.users.get(username)
        return User.from_dict(self.public(record)) if record else None

    def verify(self, username: str, password: str) -> User | None:
        record = self.users.get(username)
        # Always run a hash verification, even for a nonexistent user or
        # one without a password_hash, using a fixed dummy hash -- so the
        # time this takes doesn't depend on whether the username is real.
        password_hash = record["password_hash"] if record and record.get("password_hash") else self._dummy_password_hash
        password_matches = self.hasher.verify(password, password_hash)
        if not record or record.get("active", True) is False or not record.get("password_hash"):
            return None
        return self.user(username) if password_matches else None

    def validate_password(self, password: str) -> None:
        errors = self.password_validator.validate(password)
        if errors:
            raise ValueError(errors[0])

    async def login(self, username: str, password: str, otp: str | None = None, client_key: str | None = None) -> str | None:
        keys = {username.strip().lower(), f"ip:{client_key}" if client_key else ""}
        keys.discard("")
        now = time.time()
        failures = {
            key: [stamp for stamp in self._login_failures.get(key, []) if stamp > now - 300]
            for key in keys
        }
        if any(len(values) >= 10 for values in failures.values()):
            return None
        user = self.verify(username, password)
        if user is None:
            for key, values in failures.items():
                values.append(now)
                self._login_failures[key] = values
            return None
        record = self.users[username]
        if record.get("mfa_secret"):
            code = otp or ""
            if not self.verify_otp(record["mfa_secret"], code) and not self.consume_recovery_code(username, code):
                return None
        for key in keys:
            self._login_failures.pop(key, None)
        return await self.backend.create_token(user)

    @staticmethod
    def generate_mfa_secret() -> str:
        return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

    @staticmethod
    def verify_otp(secret: str, code: str, timestamp: int | None = None) -> bool:
        if not code or not secret:
            return False
        try:
            key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
            counter = int((timestamp or int(time.time())) // 30)
            for offset in (-1, 0, 1):
                message = (counter + offset).to_bytes(8, "big")
                digest = hmac.new(key, message, hashlib.sha1).digest()
                position = digest[-1] & 0x0F
                number = (int.from_bytes(digest[position:position + 4], "big") & 0x7FFFFFFF) % 1000000
                if hmac.compare_digest(f"{number:06d}", str(code).strip()):
                    return True
        except (ValueError, TypeError):
            return False
        return False

    def begin_mfa_setup(self, username: str, issuer: str = "Flaxon Admin") -> tuple[str, list[str]]:
        record = self.users.get(username)
        if record is None:
            raise ValueError("User not found")
        secret = self.generate_mfa_secret()
        recovery_codes = [secrets.token_urlsafe(9) for _ in range(10)]
        record["mfa_pending_secret"] = secret
        record["mfa_pending_recovery_codes"] = [self.hasher.hash(code) for code in recovery_codes]
        account = quote(record.get("email") or username, safe="")
        encoded_issuer = quote(issuer, safe="")
        uri = f"otpauth://totp/{encoded_issuer}:{account}?secret={secret}&issuer={encoded_issuer}"
        return uri, recovery_codes

    def confirm_mfa_setup(self, username: str, code: str) -> bool:
        record = self.users.get(username)
        secret = record.get("mfa_pending_secret") if record else None
        if not secret or not self.verify_otp(secret, code):
            return False
        record["mfa_secret"] = secret
        record["mfa_recovery_codes"] = record.pop("mfa_pending_recovery_codes", [])
        record.pop("mfa_pending_secret", None)
        return True

    def consume_recovery_code(self, username: str, code: str) -> bool:
        record = self.users.get(username)
        if not record or not code:
            return False
        codes = record.get("mfa_recovery_codes", [])
        for index, hashed in enumerate(codes):
            if self.hasher.verify(code.strip(), hashed):
                codes.pop(index)
                return True
        return False

    def authorize(self, user: User, permission: str) -> None:
        assigned = {item for role in user.roles for item in self.role_permissions.get(role, [])}
        if user.has_permission("admin:superuser") or user.has_permission(permission) or permission in assigned:
            return
        raise Forbidden("Insufficient admin permissions")

    async def current_user(self, request: Request) -> User:
        user = getattr(request, "user", None) or await self.backend.authenticate(request)
        if user is None:
            raise Unauthorized("Authentication required")
        request.user = user
        return user

    async def logout(self, request: Request) -> None:
        token = request.cookies.get("session_id")
        if token:
            await self.backend.revoke_token(token)

    def request_password_reset(self, identifier: str, expires_in: int = 3600) -> str | None:
        value = identifier.strip().lower()
        record = next((item for item in self.users.values() if item.get("username", "").lower() == value or item.get("email", "").lower() == value), None)
        if record is None or record.get("active", True) is False:
            return None
        token = secrets.token_urlsafe(32)
        self._reset_tokens[token] = {"username": record["username"], "expires_at": time.time() + expires_in}
        self._persist_auth_tokens()
        return token

    def reset_password(self, token: str, password: str) -> bool:
        entry = self._reset_tokens.get(token)
        if isinstance(entry, (tuple, list)):
            entry = {"username": entry[0], "expires_at": entry[1]}
        if entry is None or entry.get("expires_at", 0) < time.time() or not password:
            return False
        record = self.users.get(entry["username"])
        if record is None or record.get("active", True) is False:
            return False
        if self.password_validator.validate(password):
            return False
        record["password_hash"] = self.hasher.hash(password)
        self._reset_tokens.pop(token, None)
        self._persist_auth_tokens()
        return True

    def request_email_verification(self, username: str, expires_in: int = 86400) -> str | None:
        record = self.users.get(username)
        if record is None or not record.get("email") or record.get("email_verified"):
            return None
        token = secrets.token_urlsafe(32)
        self._verification_tokens[token] = {"username": username, "expires_at": time.time() + expires_in}
        self._persist_auth_tokens()
        return token

    def verify_email(self, token: str) -> bool:
        entry = self._verification_tokens.pop(token, None)
        if isinstance(entry, (tuple, list)):
            entry = {"username": entry[0], "expires_at": entry[1]}
        self._persist_auth_tokens()
        if entry is None or entry.get("expires_at", 0) < time.time():
            return False
        record = self.users.get(entry["username"])
        if record is None:
            return False
        record["email_verified"] = True
        return True

    def attach_cookie(self, response: Response, token: str, max_age: int = 86400) -> None:
        response.headers.add("set-cookie", f"session_id={token}; Max-Age={max_age}; Path=/; HttpOnly; SameSite=Lax")

    def clear_cookie(self, response: Response) -> None:
        response.headers.add("set-cookie", "session_id=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax")


class AdminStore:
    """SQLite-backed JSON store for admin metadata and CMS records.

    Applications can provide a different repository by implementing the same
    get/set/delete/list methods. SQLite keeps the built-in admin useful across
    restarts without introducing a required database dependency.
    """

    def __init__(self, path: str = "flaxon-admin.sqlite3") -> None:
        self.path = path
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS flaxon_admin_store (namespace TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(namespace, key))")
            db.execute("CREATE TABLE IF NOT EXISTS flaxon_admin_operations (id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL)")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=30, isolation_level="IMMEDIATE")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._connect() as db:
            row = db.execute("SELECT value FROM flaxon_admin_store WHERE namespace=? AND key=?", (namespace, key)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, namespace: str, key: str, value: Any) -> None:
        encoded = json.dumps(value, default=str)
        with self._connect() as db:
            db.execute("INSERT INTO flaxon_admin_store(namespace,key,value) VALUES(?,?,?) ON CONFLICT(namespace,key) DO UPDATE SET value=excluded.value", (namespace, key, encoded))

    def delete(self, namespace: str, key: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM flaxon_admin_store WHERE namespace=? AND key=?", (namespace, key))

    def list(self, namespace: str) -> dict[str, Any]:
        with self._connect() as db:
            rows = db.execute("SELECT key,value FROM flaxon_admin_store WHERE namespace=?", (namespace,)).fetchall()
        return {key: json.loads(value) for key, value in rows}

    def record_operation(self, kind: str, payload: dict[str, Any], operation_id: str | None = None) -> str:
        operation_id = operation_id or secrets.token_hex(8)
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO flaxon_admin_operations(id, kind, payload, created_at) VALUES(?,?,?,?)", (operation_id, kind, json.dumps(payload, default=str), time.time()))
        return operation_id

    def list_operations(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT id, kind, payload, created_at FROM flaxon_admin_operations ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 5000)),)).fetchall()
        return [{"id": row[0], "kind": row[1], "timestamp": row[3], **(json.loads(row[2]) or {})} for row in rows]

    def prune_operations(self, before: float) -> int:
        with self._connect() as db:
            result = db.execute("DELETE FROM flaxon_admin_operations WHERE created_at < ?", (before,))
            return result.rowcount


class PostgreSQLAdminStore:
    """PostgreSQL implementation of the synchronous AdminStore contract.

    The Admin production services are intentionally synchronous, so this
    adapter uses short-lived psycopg connections while the request-facing
    application database remains async. Projects with a connection-pool
    requirement can provide their own AdminStore implementation.
    """

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("PostgreSQLAdminStore requires psycopg.") from exc
        self._psycopg = psycopg
        self._db = self._psycopg.connect(self.dsn, autocommit=True)
        with self._db.cursor() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS flaxon_admin_store "
                "(namespace VARCHAR(255) NOT NULL, key VARCHAR(255) NOT NULL, "
                "value TEXT NOT NULL, PRIMARY KEY(namespace, key))"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS flaxon_admin_operations "
                "(id VARCHAR(64) PRIMARY KEY, kind VARCHAR(128) NOT NULL, "
                "payload TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL)"
            )

    def _connect(self) -> Any:
        return self._db

    def close(self) -> None:
        if not self._db.closed:
            self._db.close()

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        db = self._connect()
        row = db.execute(
                "SELECT value FROM flaxon_admin_store WHERE namespace=%s AND key=%s",
                (namespace, key),
            ).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, namespace: str, key: str, value: Any) -> None:
        db = self._connect()
        db.execute(
                "INSERT INTO flaxon_admin_store(namespace, key, value) VALUES(%s, %s, %s) "
                "ON CONFLICT(namespace, key) DO UPDATE SET value=excluded.value",
                (namespace, key, json.dumps(value, default=str)),
            )

    def delete(self, namespace: str, key: str) -> None:
        db = self._connect()
        db.execute(
                "DELETE FROM flaxon_admin_store WHERE namespace=%s AND key=%s",
                (namespace, key),
            )

    def list(self, namespace: str) -> dict[str, Any]:
        db = self._connect()
        rows = db.execute(
                "SELECT key, value FROM flaxon_admin_store WHERE namespace=%s",
                (namespace,),
            ).fetchall()
        return {key: json.loads(value) for key, value in rows}

    def record_operation(self, kind: str, payload: dict[str, Any], operation_id: str | None = None) -> str:
        operation_id = operation_id or secrets.token_hex(8)
        db = self._connect()
        db.execute(
                "INSERT INTO flaxon_admin_operations(id, kind, payload, created_at) VALUES(%s, %s, %s, %s) "
                "ON CONFLICT(id) DO UPDATE SET kind=excluded.kind, payload=excluded.payload, created_at=excluded.created_at",
                (operation_id, kind, json.dumps(payload, default=str), time.time()),
            )
        return operation_id

    def list_operations(self, limit: int = 100) -> list[dict[str, Any]]:
        db = self._connect()
        rows = db.execute(
                "SELECT id, kind, payload, created_at FROM flaxon_admin_operations "
                "ORDER BY created_at DESC LIMIT %s",
                (max(1, min(limit, 5000)),),
            ).fetchall()
        return [{"id": row[0], "kind": row[1], "timestamp": row[3], **(json.loads(row[2]) or {})} for row in rows]

    def prune_operations(self, before: float) -> int:
        db = self._connect()
        result = db.execute("DELETE FROM flaxon_admin_operations WHERE created_at < %s", (before,))
        return result.rowcount


class AdminStoreSessionBackend:
    """Persistent single-node sessions backed by the configured AdminStore."""

    def __init__(self, store: AdminStore, prefix: str = "sessions", idle_timeout: int | None = None) -> None:
        self.store = store
        self.prefix = prefix
        self.idle_timeout = idle_timeout

    async def create_token(self, user: User, expires_in: int | None = None) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        self.store.set(self.prefix, token, {"user": user.to_dict(), "created_at": now, "last_seen": now, "expires_at": now + (expires_in or 86400)})
        return token

    async def validate_token(self, token: str) -> User | None:
        session = self.store.get(self.prefix, token)
        now = time.time()
        if not session or session.get("expires_at", 0) < now or (self.idle_timeout and session.get("last_seen", now) + self.idle_timeout < now):
            if session:
                self.store.delete(self.prefix, token)
            return None
        session["last_seen"] = now
        self.store.set(self.prefix, token, session)
        return User.from_dict(session["user"])

    async def authenticate(self, request: Request) -> User | None:
        token = request.cookies.get("session_id")
        return await self.validate_token(token) if token else None

    async def revoke_token(self, token: str) -> None:
        self.store.delete(self.prefix, token)

    async def revoke_all(self, user_id: str | int) -> int:
        removed = 0
        for token, session in self.store.list(self.prefix).items():
            if str(session.get("user", {}).get("id")) == str(user_id):
                self.store.delete(self.prefix, token)
                removed += 1
        return removed


class AdminRateLimit:
    """Rate-limit mutating requests under an admin prefix."""

    def __init__(self, app: Any, prefix: str = "/admin", requests: int = 120, window_seconds: int = 60, redis_url: str | None = None, redis_protocol: int = 2, redis_max_connections: int = 100) -> None:
        self.app = app
        self.prefix = prefix.rstrip("/")
        self.limiter = RateLimiter(requests=requests, window_seconds=window_seconds)
        self.redis_url = redis_url
        self.redis_protocol = redis_protocol
        self.redis_max_connections = redis_max_connections
        self._redis = None
        self._distributed = None

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        path = str(scope.get("path", ""))
        method = str(scope.get("method", "GET")).upper()
        if scope.get("type") == "http" and path.startswith(self.prefix) and method not in {"GET", "HEAD", "OPTIONS"}:
            if self.redis_url:
                if self._redis is None:
                    import redis.asyncio as redis
                    self._redis = redis.from_url(self.redis_url, decode_responses=True, protocol=self.redis_protocol, max_connections=self.redis_max_connections)
                    self._distributed = DistributedRateLimiter(self._redis, prefix="flaxon:admin:requests")
                client = scope.get("client")
                ip = str(client[0]) if isinstance(client, (tuple, list)) and client else "unknown"
                allowed = await self._distributed.check(f"{ip}:{path}", self.limiter.requests, self.limiter.window_seconds)
            else:
                allowed = await self.limiter.check(scope)
            if not allowed:
                from flaxon.http import JSONResponse
                await JSONResponse({"error": "Too many admin requests"}, status_code=429)(scope, receive, send)
                return
        await self.app(scope, receive, send)


class RedisAdminSessionBackend:
    """Session backend compatible with ``AdminAuth`` for multi-worker deployments."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "flaxon:admin:session",
        *,
        protocol: int = 2,
        max_connections: int = 100,
        socket_timeout: float = 5.0,
        idle_timeout: int | None = None,
    ) -> None:
        self.redis_url = redis_url
        self.prefix = prefix
        if protocol not in {2, 3}:
            raise ValueError("Redis protocol must be 2 or 3")
        self.protocol = protocol
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.idle_timeout = idle_timeout
        self.client: Any = None

    async def _client(self) -> Any:
        if self.client is None:
            import redis.asyncio as redis
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                protocol=self.protocol,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
            )
        return self.client

    def _key(self, token: str) -> str:
        return f"{self.prefix}:{token}"

    async def create_token(self, user: User, expires_in: int | None = None) -> str:
        token = uuid.uuid4().hex
        now = time.time()
        payload = {"user": user.to_dict(), "created_at": now, "last_seen": now, "expires_at": now + (expires_in or 86400)}
        await (await self._client()).setex(self._key(token), expires_in or 86400, json.dumps(payload))
        return token

    async def authenticate(self, request: Request) -> User | None:
        token = request.cookies.get("session_id")
        return await self.validate_token(token) if token else None

    async def validate_token(self, token: str) -> User | None:
        value = await (await self._client()).get(self._key(token))
        if not value:
            return None
        payload = json.loads(value)
        if "user" not in payload:
            payload = {"user": payload, "expires_at": time.time() + 86400, "last_seen": time.time()}
        now = time.time()
        if payload.get("expires_at", 0) < now or (self.idle_timeout and payload.get("last_seen", now) + self.idle_timeout < now):
            await (await self._client()).delete(self._key(token))
            return None
        payload["last_seen"] = now
        client = await self._client()
        ttl = max(1, int(payload["expires_at"] - now))
        await client.setex(self._key(token), ttl, json.dumps(payload))
        return User.from_dict(payload["user"])

    async def revoke_token(self, token: str) -> None:
        await (await self._client()).delete(self._key(token))

    async def revoke_all(self, user_id: str | int) -> int:
        client = await self._client()
        removed = 0
        async for key in client.scan_iter(match=f"{self.prefix}:*"):
            value = await client.get(key)
            if not value:
                continue
            try:
                payload = json.loads(value)
                candidate = payload.get("user", payload).get("id")
            except (TypeError, ValueError):
                continue
            if str(candidate) == str(user_id):
                removed += int(await client.delete(key))
        return removed