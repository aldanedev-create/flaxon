from __future__ import annotations

import asyncio
from types import SimpleNamespace
import pytest

from flaxon import Flaxon
from flaxon.admin.cms import CMS
from flaxon.admin.cms import CMSField, ContentType
from flaxon.admin.services import AdminStore
from flaxon.admin import AdminDashboard
from flaxon.testing import TestClient


def _client():
    app = Flaxon("cms-input-hardening")
    CMS(app, auth=None, allow_unauthenticated=True)
    return TestClient(app)


def test_comments_are_normalized_and_status_is_allowlisted():
    client = _client()
    created = client.post(
        "/admin/cms/api/comments",
        json_data={
            "content_type": "article",
            "record_id": "1",
            "author_email": "person+test@example.com<script>",
            "body": "<script>alert(1)</script><p>Safe</p>",
            "ignored": "cannot be persisted",
        },
    )
    assert created.status_code == 201
    comment = created.json()
    assert "<script" not in comment["body"].lower()
    assert "ignored" not in comment

    invalid = client.patch(
        f"/admin/cms/api/comments/{comment['id']}",
        json_data={"status": "published"},
    )
    assert invalid.status_code == 400


def test_menu_payload_is_bounded_and_normalized():
    client = _client()
    valid = client.put(
        "/admin/cms/api/menus/main",
        json_data=[{"label": "Home", "url": "/", "children": []}],
    )
    assert valid.status_code == 200
    assert valid.json()["items"][0] == {"label": "Home", "url": "/", "children": []}

    nested = {"label": "Too deep", "url": "/", "children": []}
    for _ in range(7):
        nested = {"label": "Too deep", "url": "/", "children": [nested]}
    assert client.put("/admin/cms/api/menus/deep", json_data=[nested]).status_code == 400

    too_many = [{"label": str(index), "url": "/", "children": []} for index in range(101)]
    assert client.put("/admin/cms/api/menus/large", json_data=too_many).status_code == 400


def test_filesystem_store_round_trips_cms_revisions(tmp_path):
    store = AdminStore(str(tmp_path / "admin.sqlite3"))
    first = CMS(Flaxon("cms-revisions-one"), auth=None)
    first.store = store
    content_type = first.register(ContentType("article", fields=[CMSField("title", required=True)]))
    item = content_type.create({"title": "Before"})
    content_type.update(item["id"], {"title": "After"})
    first._save(content_type)

    second = CMS(Flaxon("cms-revisions-two"), auth=None)
    second.store = store
    restored = second.register(ContentType("article", fields=[CMSField("title", required=True)]))
    assert len(restored.compare_revisions(item["id"])) == 2
    assert restored.compare_revisions(item["id"])[-1]["after"]["title"] == "After"


def test_admin_notifications_persist_and_can_be_marked_read(tmp_path):
    store = AdminStore(str(tmp_path / "admin.sqlite3"))
    app = Flaxon("notifications")
    dashboard = AdminDashboard(app, store=store, users=[{"username": "admin", "password": "Admin123!"}])
    dashboard.record_activity("updated", "article", SimpleNamespace(user=SimpleNamespace(username="admin")), "1")
    token = asyncio.run(dashboard.auth.login("admin", "Admin123!"))
    headers = {"cookie": f"session_id={token}", "x-csrf-token": dashboard.csrf_token()}
    client = TestClient(app)
    response = client.get("/admin/notifications", headers=headers)
    assert response.json()["unread"] == 1
    notification_id = response.json()["items"][0]["id"]
    marked = client.post("/admin/notifications", json_data={"ids": [notification_id]}, headers=headers)
    assert marked.status_code == 200
    assert client.get("/admin/notifications", headers=headers).json()["unread"] == 0


def test_media_thumbnail_contains_dimensions(tmp_path):
    from io import BytesIO
    from PIL import Image
    from flaxon.files import FileStorage
    from flaxon.files.upload import UploadedFile

    source = BytesIO()
    Image.new("RGB", (1200, 800), "red").save(source, format="PNG")
    source.seek(0)
    storage = FileStorage(str(tmp_path / "uploads"))
    path = storage.save(UploadedFile("hero.png", "image/png", len(source.getvalue()), source))
    thumbnail = storage.create_thumbnail(path)
    assert thumbnail is not None
    with Image.open(thumbnail) as image:
        assert image.width <= 320 and image.height <= 240


def test_media_listing_falls_back_when_thumbnail_metadata_is_stale(tmp_path):
    from flaxon.files import FileStorage

    app = Flaxon("media-stale-thumbnail")
    dashboard = AdminDashboard(app, upload_dir=str(tmp_path / "uploads"))
    storage = FileStorage(str(tmp_path / "uploads"))
    storage.save_bytes(b"image data", "flower.jpg")
    dashboard.media_metadata["flower.jpg"] = {
        "thumbnail_url": "/uploads\\thumbnails\\missing.jpg",
        "content_type": "image/jpeg",
    }

    files = asyncio.run(dashboard._media_files())

    assert files[0]["url"] == "/uploads/flower.jpg"
    assert "thumbnail_url" not in files[0]["metadata"]
