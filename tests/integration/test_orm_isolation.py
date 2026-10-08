import asyncio
from types import SimpleNamespace
import httpx
import pytest
from flaxon import Flaxon
from flaxon.db import Model, fields
from flaxon.modules import FlaxonModule


class IsolatedNote(Model):
    id = fields.IntField(primary_key=True)
    title = fields.CharField(max_length=80)


@pytest.mark.asyncio
async def test_concurrent_apps_do_not_share_database_context(tmp_path):
    def application(label):
        source = SimpleNamespace(__file__=str(tmp_path / "settings.py"), BASE_DIR=tmp_path, DEBUG=True, DATABASE_URL=f"sqlite://{tmp_path / (label + '.sqlite3')}", ALLOWED_HOSTS=["testserver"])
        app = Flaxon.from_settings(source, openapi=False)
        module = FlaxonModule("isolated", models_module=__name__)
        app.mount_module(module)
        @app.get("/notes")
        async def notes():
            return {"titles": await IsolatedNote.all().values_list("title", flat=True)}
        return app
    first, second = application("first"), application("second")
    for app, title in [(first, "First database"), (second, "Second database")]:
        await app.lifecycle.startup()
        with app.db.bind():
            await app.db.context.generate_schemas()
            await IsolatedNote.create(title=title)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=first), base_url="http://testserver") as one, httpx.AsyncClient(transport=httpx.ASGITransport(app=second), base_url="http://testserver") as two:
            responses = await asyncio.gather(one.get("/notes"), two.get("/notes"), one.get("/notes"))
            assert [r.json()["titles"] for r in responses] == [["First database"], ["Second database"], ["First database"]]
    finally:
        await first.lifecycle.shutdown()
        await second.lifecycle.shutdown()
