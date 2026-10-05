from pathlib import Path

from flaxon.modules import FlaxonModule


auth = FlaxonModule("auth", ui_dir=Path(__file__).parent / "ui")


@auth.get("/session")
async def session():
    return {"authenticated": True, "name": "Store Manager", "permissions": ["catalog.view", "orders.change"]}
