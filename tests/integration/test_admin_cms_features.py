from __future__ import annotations

import asyncio
import base64
import uuid

import pytest

from flaxon import Flaxon
from flaxon.admin import AdminDashboard
from flaxon.admin.cms import CMS, CMSField, ContentType
from flaxon.testing import TestClient


class MemoryDatabase:
    def __init__(self):
        self.values = {}

    async def execute(self, query, *args):
        if query.startswith("INSERT INTO flaxon_admin_store"):
            self.values[(args[0], args[1])] = args[2]

    async def fetch_all(self, query, *args):
        return [{"namespace": ns, "key": key, "value": value} for (ns, key), value in self.values.items()]


def _app():
    app = Flaxon("admin-features", debug=True)
    dashboard = AdminDashboard(app, users=[{"username": "admin", "password": "Admin123!"}])
    cms = CMS(app)
    cms.register(ContentType("post", fields=[CMSField("title", required=True), CMSField("body", type="richtext")]))
    token = asyncio.run(dashboard.auth.login("admin", "Admin123!"))
    headers = {"cookie": f"session_id={token}", "x-csrf-token": dashboard.csrf_token()}
    return app, dashboard, TestClient(app), headers


def _multipart(fields: dict[str, str], files: dict[str, tuple[str, str, bytes]]) -> tuple[bytes, str]:
    boundary = "----FlaxonTest" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, (filename, content_type, content) in files.items():
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n".encode()
            + content
            + b"\r\n"
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def test_cms_workflows_and_sanitization():
    _, _, client, headers = _app()
    created = client.post("/admin/cms/api/post/items", json_data={"title": "Hello", "body": "<p>safe</p><script>bad()</script>"}, headers=headers)
    assert created.status_code == 201
    record = created.json()
    assert record["body"] == "<p>safe</p>bad()"

    updated = client.put(f"/admin/cms/api/post/items/{record['id']}", json_data={"title": "Changed"}, headers=headers)
    assert updated.status_code == 200
    history = client.get(f"/admin/cms/api/post/items/{record['id']}/history", headers=headers)
    assert len(history.json()["items"]) == 2
    assert history.json()["items"][1]["changes"]["title"]["before"] == "Hello"
    assert history.json()["items"][1]["changes"]["title"]["after"] == "Changed"
    restored = client.post(f"/admin/cms/api/post/items/{record['id']}/restore/0", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["title"] == "Hello"


def test_cms_body_parser_accepts_plain_dict_form_data():
    app = Flaxon("cms-form-data")
    cms = CMS(app, auth=None)
    cms.register(ContentType("page", fields=[CMSField("title", required=True)]))

    class PlainFormRequest:
        headers = {"content-type": "multipart/form-data; boundary=test"}

        async def form(self):
            return {"title": "Form page"}

    parsed = asyncio.run(cms._body_data(PlainFormRequest()))
    assert parsed == {"title": "Form page"}
    assert cms.content_types["page"].create(parsed)["title"] == "Form page"


def test_cms_scheduled_content_publishes_when_due():
    _, _, client, headers = _app()
    created = client.post("/admin/cms/api/post/items", json_data={"title": "Scheduled", "status": "scheduled", "publish_at": "2000-01-01T00:00:00+00:00"}, headers=headers)
    assert created.status_code == 201
    listed = client.get("/admin/cms/api/post/items", headers=headers).json()["items"]
    assert listed[0]["status"] == "published"


def test_cms_image_upload_uses_admin_media_storage_and_schedule_is_visible(tmp_path):
    app = Flaxon("cms-media-workflow", debug=True)
    dashboard = AdminDashboard(
        app,
        upload_dir=str(tmp_path / "media"),
        users=[{"username": "admin", "password": "Admin123!"}],
    )
    cms = CMS(app, auth=dashboard.auth)
    cms.register(ContentType("story", fields=[CMSField("title", required=True), CMSField("hero_image", type="image")]))
    token = asyncio.run(dashboard.auth.login("admin", "Admin123!"))
    headers = {"cookie": f"session_id={token}", "x-csrf-token": dashboard.csrf_token()}
    client = TestClient(app)
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    body, content_type = _multipart(
        {"title": "Uploaded story", "status": "scheduled", "publish_at": "2099-01-01T00:00:00+00:00"},
        {"hero_image": ("hero.png", "image/png", png)},
    )

    created = client.post("/admin/cms/api/story/items", content=body, headers={**headers, "content-type": content_type})
    assert created.status_code == 201
    record = created.json()
    asset = client.get(record["hero_image"])
    assert asset.status_code == 200
    assert asset.headers["content-type"].startswith("image/png")
    assert client.get("/admin/cms/api/media", headers=headers).json()[0]["url"] == record["hero_image"]

    jobs = client.get("/admin/cms/api/scheduler/jobs", headers=headers).json()["items"]
    assert jobs[0]["id"] == f"story:{record['id']}"
    cms_page = client.get("/admin/cms/", headers=headers)
    assert cms_page.status_code == 200
    assert "cms-content-nav" in cms_page.text

    changed = client.put(
        f"/admin/cms/api/story/items/{record['id']}",
        json_data={"status": "draft"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert client.get("/admin/cms/api/scheduler/jobs", headers=headers).json()["items"][0]["state"] == "canceled"


def test_cms_resources_and_import_export():
    _, _, client, headers = _app()
    taxonomy = client.post("/admin/cms/api/taxonomies", json_data={"name": "Topics", "terms": {"engineering": ["Python"]}}, headers=headers)
    assert taxonomy.status_code == 200
    comment = client.post("/admin/cms/api/comments", json_data={"content_type": "post", "record_id": "1", "body": "Review me"}, headers=headers)
    comment_id = comment.json()["id"]
    assert client.patch(f"/admin/cms/api/comments/{comment_id}", json_data={"status": "approved"}, headers=headers).json()["status"] == "approved"
    assert client.put("/admin/cms/api/menus/main", json_data=[{"label": "Home", "url": "/"}], headers=headers).status_code == 200
    imported = client.post("/admin/cms/api/import/post", json_data=[{"title": "Imported", "body": "text"}], headers=headers)
    assert imported.status_code == 201
    invalid = client.post("/admin/cms/api/import/post", json_data=[{"body": "missing title"}], headers=headers)
    assert invalid.status_code == 422 and invalid.json()["errors"][0]["row"] == 1
    assert client.get("/admin/cms/api/export/post?format=csv", headers=headers).status_code == 200
    activity = client.get("/admin/activity/export", headers=headers)
    assert activity.status_code == 200 and "action,resource" in activity.text


def test_cms_editorial_workspaces_are_api_backed():
    _, _, client, headers = _app()
    created = client.post("/admin/cms/api/post/items", json_data={"title": "Workspace post", "status": "review"}, headers=headers)
    assert created.status_code == 201
    for section in ("calendar", "board", "review", "models", "seo", "references", "trash", "integrations"):
        response = client.get(f"/admin/cms/api/workspace/{section}", headers=headers)
        assert response.status_code == 200, section
        assert response.json()["section"] == section
    page = client.get("/admin/cms/", headers=headers)
    assert page.status_code == 200
    assert "workspaceLinks" in page.text


@pytest.mark.asyncio
async def test_cms_database_storage_contract_round_trips_records():
    database = MemoryDatabase()
    cms = CMS(Flaxon("cms-db-one", debug=True), database=database, auth=None)
    content_type = cms.register(ContentType("article", fields=[CMSField("title", required=True)]))
    await cms._load_database()
    record = content_type.create({"title": "Persistent article"})
    await cms._save_content(content_type)

    restored = CMS(Flaxon("cms-db-two", debug=True), database=database, auth=None)
    restored_type = restored.register(ContentType("article", fields=[CMSField("title", required=True)]))
    await restored._load_database()
    assert restored_type.get(record["id"])["title"] == "Persistent article"


@pytest.mark.asyncio
async def test_admin_database_storage_contract_round_trips_users():
    database = MemoryDatabase()
    first = AdminDashboard(Flaxon("admin-db-one", debug=True), database=database, users=[{"username": "owner", "password": "Secret123!"}])
    await first._persist_database()
    second = AdminDashboard(Flaxon("admin-db-two", debug=True), database=database)
    await second._load_database()
    assert second.auth.verify("owner", "Secret123!") is not None
