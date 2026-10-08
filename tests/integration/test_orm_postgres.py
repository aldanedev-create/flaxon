"""Real PostgreSQL migrations / CRUD in a dedicated disposable CI database."""
import os
import subprocess
import sys
from urllib.parse import urlsplit
import pytest
from flaxon.cli.generator import Generator


@pytest.mark.skipif(not os.getenv("FLAXON_TEST_POSTGRES_URL"), reason="Dedicated PostgreSQL test URL not supplied")
def test_postgres_generated_migrations_and_model_crud(tmp_path, monkeypatch):
    url = os.environ["FLAXON_TEST_POSTGRES_URL"]
    if not urlsplit(url).path.endswith("_test"):
        pytest.fail("Use a dedicated empty database whose name ends in _test")
    root = tmp_path / "postgres_project"
    Generator().generate(root)
    monkeypatch.setenv("DATABASE_URL", url)
    def run(*args):
        result = subprocess.run([sys.executable, "management.py", *args], cwd=root, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout
    run("check")
    run("makemigrations")
    run("migrate")
    model = root / "models.py"
    model.write_text(model.read_text().replace('    body =', '    completed = fields.BooleanField(default=False)\n    body ='))
    run("makemigrations", "--name", "add_completed")
    run("migrate")
    script = '''import asyncio
from flaxon.management import load_application
from models import ProjectNote
async def main():
    app = load_application("app:app")
    async with app.db:
        note = await ProjectNote.create(title="PostgreSQL course test")
        assert note.completed is False
        note.completed = True
        await note.save()
        assert (await ProjectNote.get(pk=note.pk)).completed is True
        await note.delete()
asyncio.run(main())
'''
    result = subprocess.run([sys.executable, "-c", script], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
