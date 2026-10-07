"""Route uuid parameters behavior and boundary cases."""

import pytest


@pytest.mark.parametrize(
    "segment,expected", [("550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440000")]
)
def test_typed_route_values(app, client, segment, expected):
    @app.get("/items/<uuid:value>")
    async def endpoint(value):
        return {"value": str(value), "kind": type(value).__name__}

    response = client.get("/items/" + segment)
    assert response.status_code == 200
    assert response.json() == {"value": expected, "kind": "UUID"}


@pytest.mark.parametrize(
    "segment", ["bad", "00000000-0000-0000-0000-00000000000Z", "------------------------------------"]
)
def test_invalid_converter_values_are_not_routes(app, client, segment):
    @app.get("/items/<uuid:value>")
    async def endpoint(value):
        return {"value": str(value)}

    assert client.get("/items/" + segment).status_code == 404


def test_missing_parameter_is_not_found(app, client):
    @app.get("/items/<uuid:value>")
    async def endpoint(value):
        return {"value": str(value)}

    assert client.get("/items/").status_code == 404
