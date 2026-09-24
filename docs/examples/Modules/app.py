"""A small catalog and order application composed from feature modules.

Run from the repository root with:

    flaxon run docs.examples.Modules.app:app --reload
"""

from pathlib import Path

from flaxon import Flaxon
from flaxon.jinax import Jinax

from .modules.catalog import catalog
from .modules.orders import orders
from .modules.store import StoreService

BASE_DIR = Path(__file__).parent

app = Flaxon("module-store", debug=True)
app.use_templates(Jinax(BASE_DIR / "templates", auto_reload=True, strict_undefined=True))

# The modules depend on this service by name. Replace this in a real project
# with a database-backed repository without changing the module boundaries.
app.container.register_instance("store", StoreService())
app.mount_module(catalog, prefix="/store")
app.mount_module(orders, prefix="/api/orders")
