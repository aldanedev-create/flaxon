from pathlib import Path

from flaxon import Flaxon, Request

from modules.auth.module import auth
from modules.catalog.module import catalog
from modules.chat.module import chat
from modules.orders.module import orders


ROOT = Path(__file__).parent
app = Flaxon("Petal & Stem", debug=True)
app.mount_module(auth, prefix="/api/auth")
app.mount_module(catalog, prefix="/api/catalog")
app.mount_module(orders, prefix="/api/orders")
app.mount_module(chat, prefix="/api/chat")
app.use_teloce(project_root=ROOT, ui_dir="ui", title="Petal & Stem Operations")


@app.get("/")
@app.get("/<path:spa_path>")
async def spa(request: Request, spa_path: str = ""):
    return await request.compile("app.html", {"store": "Petal & Stem"})
