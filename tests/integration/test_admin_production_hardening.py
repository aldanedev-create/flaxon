from __future__ import annotations

import time

import pytest

from flaxon import Flaxon
from flaxon.admin.production import DurableJobStore, ImmutableAuditLog, NotificationService, ResumableUploadStore
from flaxon.admin import AdminDashboard
from flaxon.admin.services import AdminStore
from flaxon.security.password import PasswordHasher
from flaxon.testing import TestClient


def test_admin_store_mutate_and_durable_job_history_are_atomic(tmp_path):
    store = AdminStore(str(tmp_path / "admin.sqlite3"))
    jobs = DurableJobStore(store)
    job = jobs.enqueue("example", {"value": 1}, job_id="fixed-job")
    assert jobs.enqueue("example", {"value": 2}, job_id="fixed-job").payload == {"value": 1}
    claimed = jobs.claim_due()
    assert [item.id for item in claimed] == [job.id]
    jobs.fail(job.id, "temporary", retry_delay=0)
    assert jobs.list(status="queued")[0].attempts == 1
    history = jobs.history(job.id)
    assert [item["event"] for item in history][:3] == ["retry_scheduled", "claimed", "enqueued"]


def test_audit_retention_preserves_original_hashes(tmp_path):
    log = ImmutableAuditLog(AdminStore(str(tmp_path / "audit.sqlite3")))
    first = log.append("one", "admin", {}, ip="127.0.0.1", user_agent="test")
    time.sleep(0.01)
    log.append("two", "admin", {})
    assert log.verify()
    assert log.prune(first["created_at"] + 0.001) == 1
    assert log.verify()
    assert log.store.get("audit", "entries")[0]["previous_hash"] == first["hash"]


@pytest.mark.asyncio
async def test_notification_channels_have_preferences_and_delivery_state(tmp_path):
    service = NotificationService(AdminStore(str(tmp_path / "notifications.sqlite3")))
    delivered: list[str] = []

    async def sender(channel, message):
        delivered.append(channel)

    service.register_channel("email", sender)
    result = await service.publish_async("admin", "email", {"subject": "Hello"})
    assert result["delivered"] is True
    assert delivered == ["email"]
    message = service.list("admin")[0]
    assert message["delivery_status"] == "delivered"
    service.mark_read("admin", [message["id"]])
    assert service.list("admin", unread_only=True) == []
    service.set_preferences("admin", {"email": False})
    assert (await service.publish_async("admin", "email", {}))["reason"] == "disabled"


def test_resumable_upload_requires_contiguous_offsets_and_expires(tmp_path):
    uploads = ResumableUploadStore(AdminStore(str(tmp_path / "uploads.sqlite3")))
    upload_id = uploads.create("hello.txt", 6, content_type="text/plain")
    with pytest.raises(ValueError, match="offset mismatch"):
        uploads.put_chunk(upload_id, 1, b"x")
    uploads.put_chunk(upload_id, 0, b"hel")
    assert uploads.status(upload_id)["offset"] == 3
    uploads.put_chunk(upload_id, 3, b"lo!")
    assert uploads.finalize(upload_id) == ("hello.txt", b"hello!")


def test_argon2_hasher_is_optional_and_round_trips_when_installed():
    try:
        hasher = PasswordHasher(algorithm="argon2")
    except RuntimeError:
        pytest.skip("argon2-cffi is not installed")
    value = hasher.hash("Secure123!")
    assert hasher.verify("Secure123!", value)
    assert not hasher.verify("Wrong123!", value)


def test_media_workspace_filters_signed_urls_and_bulk_actions(tmp_path):
    app = Flaxon("media-workspace")
    dashboard = AdminDashboard(
        app,
        storage_path=str(tmp_path / "admin.sqlite3"),
        upload_dir=str(tmp_path / "uploads"),
        users=[{"username": "admin", "password": "Admin123!"}],
    )
    dashboard.media.save_bytes(b"content", "documents/readme.txt")
    dashboard.media_metadata["documents/readme.txt"] = {"content_type": "text/plain", "title": "Read me"}
    dashboard.store.set("media", "metadata", dashboard.media_metadata)
    token = __import__("asyncio").run(dashboard.auth.login("admin", "Admin123!"))
    headers = {"cookie": f"session_id={token}", "x-csrf-token": dashboard.csrf_token()}
    client = TestClient(app)

    page = client.get("/admin/media?q=readme&kind=documents", headers=headers)
    assert page.status_code == 200
    assert "Media library" in page.text and "readme.txt" in page.text
    signed = client.get("/admin/media/documents/readme.txt/signed-url", headers=headers)
    assert signed.status_code == 200 and signed.json()["url"].endswith("documents/readme.txt")
    created_folder = client.post("/admin/media/folders", json_data={"name": "archive"}, headers=headers)
    assert created_folder.status_code == 200 and "archive" in created_folder.json()["folders"]
    bulk = client.post("/admin/media/bulk", json_data={"action": "delete", "names": ["documents/readme.txt"]}, headers=headers)
    assert bulk.status_code == 200 and bulk.json()["deleted"] == 1
    assert not dashboard.media.exists("documents/readme.txt")
