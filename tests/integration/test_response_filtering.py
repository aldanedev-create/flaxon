import pytest

from flaxon import Flaxon
from flaxon.http.response import JSONResponse
from flaxon.testing import TestClient

pydantic = pytest.importorskip("pydantic")


class UserOut(pydantic.BaseModel):
    id: int
    name: str


class UserDB(UserOut):
    password_hash: str


class Envelope(pydantic.BaseModel):
    user: UserOut


@pytest.mark.parametrize("kind", ["dict", "subclass", "constructed"])
def test_declared_model_filters_secrets(kind):
    app = Flaxon("output", debug=False)
    data = {"id": 1, "name": "Ada", "password_hash": "SECRET"}
    value = data if kind == "dict" else UserDB(**data)
    if kind == "constructed":
        value = UserDB.model_construct(**data)

    @app.get("/")
    async def user() -> UserOut:
        return value

    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Ada"}


def test_nested_and_list_models_are_filtered():
    app = Flaxon("nested")
    secret = UserDB(id=1, name="Ada", password_hash="SECRET")

    @app.get("/nested")
    async def nested() -> Envelope:
        return Envelope(user=secret)

    @app.get("/list")
    async def users() -> list[UserOut]:
        return [secret, {"id": 2, "name": "Ben", "password_hash": "OTHER"}]

    client = TestClient(app)
    assert client.get("/nested").json() == {"user": {"id": 1, "name": "Ada"}}
    assert client.get("/list").json() == [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Ben"}]


def test_invalid_output_is_server_error_and_explicit_response_bypasses():
    app = Flaxon("invalid", debug=False)

    @app.get("/invalid")
    async def invalid() -> UserOut:
        return UserOut.model_construct(id="invalid", name="Ada")

    @app.get("/explicit")
    async def explicit() -> UserOut:
        return JSONResponse({"custom": True}, status_code=201)

    client = TestClient(app)
    response = client.get("/invalid")
    assert response.status_code == 500
    assert "invalid" not in response.text
    assert client.get("/explicit").status_code == 201
    assert client.get("/explicit").json() == {"custom": True}


def test_validation_aliases_survive_instance_revalidation():
    class Aliased(pydantic.BaseModel):
        name: str = pydantic.Field(validation_alias=pydantic.AliasPath("names", 0))

    from flaxon.integrations.pydantic import filter_response, prepare_response_adapter

    value = Aliased.model_validate({"names": ["Ada"]})
    assert filter_response(prepare_response_adapter(Aliased), value) == {"name": "Ada"}
