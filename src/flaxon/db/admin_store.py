"""ORM persistence with a synchronous facade for existing Admin services.

A dedicated loop owns these connections; request-loop connections are never
shared with the synchronous facade. Schema creation remains a management task.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import threading
import time
from tortoise.context import TortoiseContext, _current_context
from tortoise.transactions import in_transaction
from .storemodels import AdminEntry, AdminOperation


class ORMAdminStore:
    def __init__(self, database_url):
        self.loop = asyncio.new_event_loop()
        self.context = TortoiseContext()
        self.lock = threading.RLock()
        self.closed = False
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True, name="flaxon-admin-store")
        self.thread.start()
        try:
            self._run(
                self.context.init(
                    config={
                        "connections": {"default": database_url},
                        "apps": {
                            "flaxon_admin": {
                                "models": ["flaxon.db.storemodels"],
                                "default_connection": "default",
                            }
                        },
                    }
                )
            )
        except Exception:
            self.close()
            raise

    def _run(self, coroutine):
        async def bound():
            token = _current_context.set(self.context)
            try:
                return await coroutine
            finally:
                _current_context.reset(token)

        with self.lock:
            if self.closed:
                close = getattr(coroutine, "close", None)
                if close:
                    close()
                raise RuntimeError("Admin store is closed")
            future = asyncio.run_coroutine_threadsafe(bound(), self.loop)
        return future.result()

    @staticmethod
    def _id(namespace, key):
        return hashlib.sha256(f"{namespace}\0{key}".encode()).hexdigest()

    def get(self, namespace, key, default=None):
        async def read():
            row = await AdminEntry.get_or_none(pk=self._id(namespace, key))
            return row.value if row else default

        return self._run(read())

    def set(self, namespace, key, value):
        async def write():
            await AdminEntry.update_or_create(
                id=self._id(namespace, key),
                defaults={
                    "namespace": namespace,
                    "key": key,
                    "value": json.loads(json.dumps(value, default=str)),
                },
            )

        return self._run(write())

    def mutate(self, namespace, key, callback, default=None):
        async def change():
            async with in_transaction():
                # Ensure even the first mutation has a row to lock.
                await AdminEntry.get_or_create(
                    id=self._id(namespace, key),
                    defaults={"namespace": namespace, "key": key, "value": default},
                )
                row = await AdminEntry.select_for_update().get(pk=self._id(namespace, key))
                value = row.value
                # Existing services may read this store from inside a mutation.
                # Run their synchronous callback off the store loop so nested
                # reads can execute on that loop within this transaction.
                result = await asyncio.to_thread(callback, value)
                row.value = json.loads(json.dumps(value, default=str))
                await row.save(update_fields=["value"])
                return result

        return self._run(change())

    def delete(self, namespace, key):
        return self._run(AdminEntry.filter(id=self._id(namespace, key)).delete())

    def list(self, namespace):
        async def read():
            return {row.key: row.value for row in await AdminEntry.filter(namespace=namespace)}

        return self._run(read())

    def record_operation(self, kind, payload, operation_id=None):
        identifier = operation_id or secrets.token_hex(8)

        async def write():
            await AdminOperation.update_or_create(
                id=identifier,
                defaults={
                    "kind": kind,
                    "payload": json.loads(json.dumps(payload, default=str)),
                    "created_at": time.time(),
                },
            )
            return identifier

        return self._run(write())

    def list_operations(self, limit=100):
        async def read():
            rows = await AdminOperation.all().order_by("-created_at").limit(max(1, min(limit, 5000)))
            return [
                {"id": row.id, "kind": row.kind, "timestamp": row.created_at, **row.payload} for row in rows
            ]

        return self._run(read())

    def prune_operations(self, before):
        return self._run(AdminOperation.filter(created_at__lt=before).delete())

    def close(self):
        if not self.closed:
            try:
                self._run(self.context.close_connections())
            finally:
                self.closed = True
                self.loop.call_soon_threadsafe(self.loop.stop)
                self.thread.join(timeout=10)
                self.loop.close()

    def import_sqlite(self, source_path):
        """Copy a legacy store atomically, refusing a nonempty destination."""
        import json
        import sqlite3
        from pathlib import Path

        source = Path(source_path).resolve()
        if not source.is_file():
            raise ValueError("Legacy Admin store does not exist")
        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as db:
            entries = db.execute("SELECT namespace, key, value FROM flaxon_admin_store").fetchall()
            operations = db.execute(
                "SELECT id, kind, payload, created_at FROM flaxon_admin_operations"
            ).fetchall()

        async def copy():
            async with in_transaction():
                if await AdminEntry.all().exists() or await AdminOperation.all().exists():
                    raise ValueError("Destination Admin store must be empty")
                for namespace, key, encoded in entries:
                    await AdminEntry.create(
                        id=self._id(namespace, key), namespace=namespace, key=key, value=json.loads(encoded)
                    )
                for identifier, kind, encoded, timestamp in operations:
                    await AdminOperation.create(
                        id=identifier, kind=kind, payload=json.loads(encoded), created_at=timestamp
                    )
            return {"entries": len(entries), "operations": len(operations)}

        return self._run(copy())
