"""Verify the public generated-project workflow, not just adapter internals."""
import subprocess
import sys

from flaxon.cli.generator import Generator


def command(root, *args):
    result = subprocess.run([sys.executable, str(root / "management.py"), *args], cwd=root.parent, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_generated_python_migration_workflow(tmp_path):
    root = tmp_path / "project_manager"
    Generator().generate(root)
    assert not list(root.rglob("*.json"))
    assert "passed" in command(root, "check")
    assert not (root / "data/admin.sqlite3").exists()
    assert "0001_initial" in command(root, "makemigrations")
    assert "APPLY" in command(root, "migrate", "--plan")
    assert "OK" in command(root, "migrate")
    assert "0001_initial" in command(root, "migrate", "--status")
    assert "No migrations to apply" in command(root, "migrate")
    models = root / "models.py"
    models.write_text(models.read_text().replace('    body =', '    priority = fields.IntField(default=0)\n    body ='))
    assert "0002" in command(root, "makemigrations", "--name", "add_priority")
    command(root, "migrate")
    import sqlite3
    with sqlite3.connect(root / "data/app.sqlite3") as connection:
        names = {row[1] for row in connection.execute("PRAGMA table_info(project_notes)")}
        assert "priority" in names
    assert "Welcome" in command(root, "welcome")
    assert "Teloce" in command(root, "welcome-status")


def test_generated_admin_navigation_crud_and_csrf(tmp_path):
    root = tmp_path / "project_manager"
    Generator().generate(root)
    command(root, "makemigrations")
    command(root, "migrate")
    # Run in a separate interpreter to isolate project imports from other tests.
    script = r'''
import asyncio, re, secrets
import httpx
from app import app

async def main():
    dashboard = app._flaxon_admin_dashboard
    password = secrets.token_urlsafe(20) + "Aa1!"
    dashboard.auth.add_user({"username": "operator", "password": password, "permissions": ["admin.superuser"]})
    await app.lifecycle.startup()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            login = await client.get("/admin/login")
            csrf = re.search(r'name="_csrf" value="([^"]+)"', login.text).group(1)
            signed_in = await client.post("/admin/login", data={"username": "operator", "password": password, "_csrf": csrf})
            assert signed_in.status_code == 302, signed_in.text
            index = await client.get("/admin/")
            assert '/admin/services"' not in index.text
            assert '/admin/health"' not in index.text
            assert '/admin/cms/' in index.text
            for path in ["/", "/server-page", "/api/welcome/status", "/admin/", "/admin/users", "/admin/roles", "/admin/media", "/admin/settings", "/admin/activity", "/admin/operations", "/admin/profile", "/admin/notifications", "/admin/cms/", "/admin/projectnote", "/admin/projectnote/add"]:
                response = await client.get(path)
                assert response.status_code == 200, (path, response.status_code, response.text[:400])
            form = await client.get("/admin/projectnote/add")
            token = re.search(r'name="_csrf" value="([^"]+)"', form.text).group(1)
            response = await client.post("/admin/projectnote/add", data={"_csrf": token, "title": "Readable project", "body": "Notes"})
            assert response.status_code == 302, response.text
            response = await client.get("/admin/projectnote?q=Readable")
            assert "Readable project" in response.text
            assert (await client.get("/admin/projectnote?page=bad")).status_code == 400
            assert (await client.get("/admin/projectnote?order_by=not_a_field")).status_code == 400
            assert (await client.get("/admin/projectnote/99999/edit")).status_code == 404
            invalid = await client.post("/admin/projectnote/add", data={"_csrf": token, "title": "x" * 201})
            assert invalid.status_code == 400, invalid.text
            forged = await client.post("/admin/projectnote/add", data={"_csrf": token, "title": "Blocked"}, headers={"Origin": "https://attacker.example"})
            assert forged.status_code == 403
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as other:
                await other.get("/admin/login")
                stolen = await other.post("/admin/login", data={"username": "operator", "password": password, "_csrf": token})
                assert stolen.status_code == 403, stolen.text
            assert (await client.post("/admin/cms/api/page/items", json={"title": "Page", "status": "draft"}, headers={"x-csrf-token": token})).status_code == 201
        print("Admin navigation, model CRUD, validation and CSRF passed")
    finally:
        await app.lifecycle.shutdown()
asyncio.run(main())
'''
    result = subprocess.run([sys.executable, "-c", script], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_module_model_discovery_and_foreign_keys(tmp_path):
    root = tmp_path / "project_manager"
    Generator().generate(root)
    feature = root / "modules/projects"
    feature.mkdir()
    (feature / "__init__.py").write_text("")
    (feature / "models.py").write_text('''from flaxon.db import Model, fields
class Project(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=80)
    note = fields.ForeignKeyField("models.ProjectNote", related_name="projects")
''')
    (feature / "module.py").write_text('''from flaxon.modules import FlaxonModule
projects = FlaxonModule("projects", models_module="modules.projects.models")
''')
    (feature / "admin.py").write_text('''from .models import Project
def register(admin):
    admin.register(Project, search_fields=["name"])
''')
    app = root / "app.py"
    app.write_text(app.read_text().replace('from modules.welcome.module import welcome', 'from modules.welcome.module import welcome\nfrom modules.projects.module import projects').replace('    # Management discovers', '    app.mount_module(projects, prefix="/projects")\n\n    # Management discovers'))
    command(root, "check")
    output = command(root, "makemigrations")
    assert "projects.0001_initial" in output
    command(root, "migrate")
    assert (feature / "migrations/0001_initial.py").exists()
