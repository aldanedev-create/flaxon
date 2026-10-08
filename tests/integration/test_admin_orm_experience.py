"""Exercise relationship authorization, atomic writes and editing in a real project."""

import subprocess
import sys
from flaxon.cli.generator import Generator
from tests.integration.test_orm_management import command


def test_admin_orm_experience(tmp_path):
    root = tmp_path / "admin_experience"
    Generator().generate(root)
    (root / "models.py").write_text("""from flaxon.db import Model, fields
class Project(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50, unique=True)
    visible = fields.BooleanField(default=True)
class Task(Model):
    id = fields.IntField(primary_key=True)
    title = fields.CharField(max_length=50)
    project = fields.ForeignKeyField("models.Project", related_name="tasks", on_delete=fields.CASCADE)
class Team(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50)
    projects = fields.ManyToManyField("models.Project", related_name="teams")
""")
    (root / "admin.py").write_text("""from models import Project, Task, Team
def register(admin):
    admin.register(Project, search_fields=["name"], can_view=lambda user, obj: obj.visible,
        queryset=lambda user, query: query.filter(visible=True),
        inlines={"tasks": {"model": Task, "fk": "project_id"}}, fieldsets={"Details": ["name", "visible"]})
    admin.register(Task, search_fields=["title"], can_delete=lambda user, obj: obj.title != "Protected")
    admin.register(Team)
""")
    settings = root / "settings.py"
    settings.write_text(settings.read_text() + '\nADMIN_STORE_BACKEND = "orm"\n')
    assert "flaxon_admin" in command(root, "makemigrations")
    command(root, "migrate")
    script = r"""
import asyncio, secrets, json
from types import SimpleNamespace
from app import app
from models import Project, Task, Team
from flaxon.db.admin import admin_context
from flaxon.exceptions import Forbidden, Conflict, BadRequest
from flaxon.admin.services import AdminStore
from pathlib import Path

async def main():
    dashboard = app._flaxon_admin_dashboard
    password = secrets.token_urlsafe(25) + "Aa1!"
    record = dashboard.auth.add_user({"username": "operator", "password": password, "permissions": ["admin.superuser"]})
    dashboard.store.set("users", "operator", record)
    await app.lifecycle.startup()
    try:
        with app.db.bind():
            from flaxon.security import User
            user = User(id="operator", username="operator", permissions=["admin.superuser"])
            admin_context.set((dashboard, user))
            project = dashboard.registry.get("project").model
            task = dashboard.registry.get("task").model
            team = dashboard.registry.get("team").model
            visible = await Project.create(name="Allowed")
            hidden = await Project.create(name="Hidden", visible=False)
            field = task.relationship_fields["project_id"]
            assert [row.pk for row in await task.related_rows(field)] == [visible.pk]
            try:
                await task.create_instance({"title": "No", "project_id": hidden.pk})
                raise AssertionError("Hidden relationship accepted")
            except Forbidden:
                pass
            item = await task.create_instance({"title": "One", "project_id": visible.pk})
            version = await task.version(item)
            await Task.filter(pk=item.pk).update(title="Elsewhere")
            try:
                await task.update_instance(item.pk, {"title": "Overwrite"}, expected_version=version)
                raise AssertionError("Stale write accepted")
            except Conflict:
                pass
            assert (await Task.get(pk=item.pk)).title == "Elsewhere"
            await team.create_instance({"name": "Staff", "projects": json.dumps([visible.pk])})
            assert await (await Team.first()).projects.all().count() == 1
            team_record = await Team.first()
            team_version = await team.version(team_record)
            await team_record.projects.clear()
            try:
                await team.update_instance(team_record.pk, {"name": "Stale team"}, expected_version=team_version)
                raise AssertionError("Concurrent relationship edit accepted")
            except Conflict:
                pass
            try:
                await team.create_instance({"name": "Blocked", "projects": json.dumps([hidden.pk])})
                raise AssertionError("Hidden M2M accepted")
            except Forbidden:
                pass
            parent = await project.create_instance({"name": "With tasks", "_inline_tasks": json.dumps([{"title": "Child"}])})
            assert await Task.filter(project_id=parent.pk).count() == 1
            try:
                await project.update_instance(parent.pk, {"name": "Broken", "_inline_tasks": json.dumps([{"id": item.pk, "title": "Hijack"}])})
                raise AssertionError("Cross-parent inline accepted")
            except Forbidden:
                pass
            assert (await Project.get(pk=parent.pk)).name == "With tasks"
            result = await project.query(page=1, per_page=1)
            assert result["total"] == 2 and result["pages"] == 2
            preview = await project.deletion_preview(parent.pk)
            assert preview[0]["count"] == 1 and preview[0]["behavior"] == "CASCADE"
            protected = await Project.create(name="Protected parent")
            await Task.create(title="Protected", project_id=protected.pk)
            try:
                await project.delete_instance(protected.pk)
                raise AssertionError("Protected child deleted through cascade")
            except Forbidden:
                pass
            assert await Project.filter(pk=protected.pk).exists()
            for number in range(101):
                await Project.create(name=f"Project {number}")
            assert (await task.form_schema())["project_id"]["kind"] == "autocomplete"
            assert "Hidden" not in [row.name for row in await task.related_rows(field)]
            # A late duplicate failure must roll back an earlier successful insert.
            before = await Project.all().count()
            try:
                async with project.transaction():
                    await project.create_instance({"name": "Rollback"})
                    await project.create_instance({"name": "Allowed"})
            except Conflict:
                pass
            assert await Project.all().count() == before
            # Permission-scoped endpoints and error forms use actual authenticated HTTP.
            import httpx, re
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
                login = await client.get("/admin/login")
                csrf = re.search(r'name="_csrf" value="([^"]+)"', login.text).group(1)
                assert (await client.post("/admin/login", data={"username": "operator", "password": password, "_csrf": csrf})).status_code == 302
                form = await client.get("/admin/task/add")
                assert form.status_code == 200, form.text
                csrf = re.search(r'name="_csrf" value="([^"]+)"', form.text).group(1)
                choices = await client.get("/admin/task/relationships/project_id?q=Project&page=2")
                assert choices.status_code == 200 and len(choices.json()["items"]) == 25
                invalid = await client.post("/admin/task/add", data={"_csrf": csrf, "title": "x" * 51, "project_id": visible.pk})
                assert invalid.status_code == 400 and "Enter a valid value" in invalid.text
                assert "x" * 51 in invalid.text
                edit = await client.get(f"/admin/task/{item.pk}/edit")
                assert edit.status_code == 200, edit.text
                version = re.search(r'name="_version" value="([^"]+)"', edit.text).group(1)
                invalid_edit = await client.post(f"/admin/task/{item.pk}/edit", data={"_csrf": csrf, "_version": version, "title": "x" * 51, "project_id": visible.pk})
                assert invalid_edit.status_code == 400 and "Enter a valid value" in invalid_edit.text, invalid_edit.text
                error = await client.post("/admin/project/import", json=[{"name": "Atomic"}, {"name": "Allowed"}], headers={"x-csrf-token": csrf})
                assert error.status_code == 422, error.text
                assert not await Project.filter(name="Atomic").exists()
    finally:
        await app.lifecycle.shutdown()
    # Existing metadata survived the ORM connection lifecycle.
    from flaxon.db.admin_store import ORMAdminStore
    store = ORMAdminStore(app.settings.DATABASE_URL)
    try:
        assert store.get("users", "operator")["username"] == "operator"
        assert store.mutate("test", "counter", lambda value: value.update(count=value["count"] + 1), default={"count": 0}) is None
        assert store.get("test", "counter")["count"] == 1
        from flaxon.admin.production import ImmutableAuditLog
        audit = ImmutableAuditLog(store)
        audit.append("verified", "operator", {"test": True})
        assert audit.verify()
    finally:
        store.close()
asyncio.run(main())
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_legacy_admin_store_copy(tmp_path):
    from flaxon.admin.services import AdminStore

    root = tmp_path / "store_copy"
    Generator().generate(root)
    settings = root / "settings.py"
    settings.write_text(settings.read_text() + '\nADMIN_STORE_BACKEND = "orm"\n')
    command(root, "makemigrations")
    command(root, "migrate")
    legacy = tmp_path / "legacy.sqlite3"
    source = AdminStore(str(legacy))
    source.set("cms", "draft", {"title": "Preserved"})
    source.record_operation("test", {"value": 7}, "example")
    assert "entries" in command(root, "migrate-admin-store", str(legacy))
    script = """from settings import DATABASE_URL
from flaxon.db.admin_store import ORMAdminStore
store = ORMAdminStore(DATABASE_URL)
try:
    assert store.get("cms", "draft")["title"] == "Preserved"
    assert store.list_operations()[0]["value"] == 7
finally:
    store.close()
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    result = subprocess.run(
        [sys.executable, "management.py", "migrate-admin-store", str(legacy)],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "must be empty" in result.stderr
    assert source.get("cms", "draft")["title"] == "Preserved"
