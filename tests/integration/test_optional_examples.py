from examples.fastmcp_app.app import app as fastmcp_app
from examples.pydantic_api.app import app as pydantic_app

from flaxon.testing import TestClient


def test_pydantic_example_exposes_mounted_module() -> None:
    response = TestClient(pydantic_app).post(
        "/api/users/",
        json_data={"name": "Ava", "email": "ava@example.com", "age": 28},
    )

    assert response.status_code == 200
    assert response.json() == {
        "name": "Ava",
        "email": "ava@example.com",
        "age": 28,
    }


def test_fastmcp_example_keeps_feature_http_route() -> None:
    response = TestClient(fastmcp_app).get("/store/status")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "feature": "store"}
