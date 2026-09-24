from __future__ import annotations

import pytest

from flaxon import Flaxon, Query, Router
from flaxon.testing import TestClient
from flaxon.validation import IntField, Schema, StrField

try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None

if BaseModel is not None:
    class ProductPayload(BaseModel):
        name: str
        price: float


class UserPayload(Schema):
    name = StrField(required=True, description="Display name")
    age = IntField(minimum=0)


def test_constructor_enables_openapi_and_infers_routes():
    app = Flaxon("catalog", openapi=True)

    @app.get(
        "/users/<int:user_id>",
        summary="Get a user",
        tags=["users"],
        operation_id="get_user",
    )
    async def get_user(user_id: int, limit: int = Query(20, ge=1, le=100, description="Page size")) -> UserPayload:
        return {"name": f"User {user_id}"}

    @app.post("/users", responses={201: (UserPayload, "Created")})
    async def create_user(user: UserPayload) -> UserPayload:
        return user

    client = TestClient(app)
    spec_response = client.get("/openapi.json")
    assert spec_response.status_code == 200
    spec = spec_response.json()

    operation = spec["paths"]["/users/{user_id}"]["get"]
    assert operation["summary"] == "Get a user"
    assert operation["operationId"] == "get_user"
    assert operation["tags"] == ["users"]
    assert operation["parameters"][0]["schema"] == {"type": "integer"}
    query = operation["parameters"][1]
    assert query["name"] == "limit"
    assert query["schema"]["default"] == 20
    assert query["schema"]["minimum"] == 1
    assert query["required"] is False

    create_operation = spec["paths"]["/users"]["post"]
    assert create_operation["requestBody"]["required"] is True
    assert create_operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/UserPayload"
    }
    assert create_operation["responses"]["201"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/UserPayload"
    }
    assert spec["components"]["schemas"]["UserPayload"]["required"] == ["name"]
    assert client.get("/docs").status_code == 200
    assert "SwaggerUIBundle" in client.get("/docs").text
    assert client.get("/redoc").status_code == 200
    assert "redoc" in client.get("/redoc").text


def test_query_parameters_are_coerced_and_validated():
    app = Flaxon("query")

    @app.get("/search")
    async def search(limit: int = Query(10, ge=1), include_archived: bool = Query(False)):
        return {"limit": limit, "include_archived": include_archived}

    client = TestClient(app)
    assert client.get("/search?limit=3&include_archived=true").json() == {
        "limit": 3,
        "include_archived": True,
    }
    assert client.get("/search?limit=bad").status_code == 422
    assert client.get("/search?limit=0").status_code == 422


def test_openapi_preserves_metadata_through_router_mount():
    router = Router(prefix="/v1")

    @router.get("/health", summary="Module health", tags=["system"])
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app = Flaxon("mounted", openapi=True)
    app.include_router(router, prefix="/api")
    operation = TestClient(app).get("/openapi.json").json()["paths"]["/api/health"]["get"]
    assert operation["summary"] == "Module health"
    assert operation["tags"] == ["system"]
    assert operation["operationId"] == "health"


def test_documentation_guard_protects_spec_and_ui():
    app = Flaxon("protected")
    app.enable_openapi(docs_guard=lambda request: request.headers.get("x-docs-key") == "letmein")
    client = TestClient(app)
    assert client.get("/openapi.json").status_code == 403
    assert client.get("/docs").status_code == 403
    assert client.get("/redoc", headers={"x-docs-key": "letmein"}).status_code == 200


@pytest.mark.skipif(__import__("importlib").util.find_spec("pydantic") is None, reason="pydantic is optional")
def test_pydantic_models_are_exported_when_installed():
    app = Flaxon("pydantic", openapi=True)

    @app.post("/products")
    async def create_product(product: ProductPayload) -> ProductPayload:
        return product

    spec = TestClient(app).get("/openapi.json").json()
    assert spec["components"]["schemas"]["ProductPayload"]["properties"]["price"]["type"] == "number"
    assert spec["paths"]["/products"]["post"]["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ProductPayload"
    }
