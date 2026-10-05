from pathlib import Path

from flaxon.modules import FlaxonModule


orders = FlaxonModule("orders", ui_dir=Path(__file__).parent / "ui")


@orders.get("")
async def order_list():
    return {"items": [{"number": "PS-1042", "customer": "Maya Brown", "status": "Preparing"}]}
