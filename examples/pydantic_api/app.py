from examples.pydantic_api.modules.users import users
from flaxon import Flaxon


def create_app() -> Flaxon:
    app = Flaxon("pydantic-api", debug=True)
    app.mount_module(users, prefix="/api/users")
    return app


app = create_app()
