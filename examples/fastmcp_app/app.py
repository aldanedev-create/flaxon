"""Run with: flaxon run examples.fastmcp_app.app:app --reload"""

from examples.fastmcp_app.modules.store import install_store
from flaxon import Flaxon


def create_app() -> Flaxon:
    app = Flaxon("fastmcp-example", debug=True)
    install_store(app, allow_unauthenticated_local_mcp=True)
    return app


app = create_app()
