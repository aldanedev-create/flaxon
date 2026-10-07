"""Route int parameters behavior and boundary cases."""

import pytest


@pytest.mark.parametrize("segment,expected", [("0", "0"), ("-7", "-7"), ("999999999999", "999999999999")])
def test_typed_route_values(app, client, segment, expected):
    @app.get("/items/<int:value>")
    async def endpoint(value):
        return {"value": str(value), "kind": type(value).__name__}

    response = client.get("/items/" + segment)
    assert response.status_code == 200
    assert response.json() == {"value": expected, "kind": "int"}


@pytest.mark.parametrize("segment", ["1.5", "abc", "12x"])
def test_invalid_converter_values_are_not_routes(app, client, segment):
    @app.get("/items/<int:value>")
    async def endpoint(value):
        return {"value": str(value)}

    assert client.get("/items/" + segment).status_code == 404


def test_missing_parameter_is_not_found(app, client):
    @app.get("/items/<int:value>")
    async def endpoint(value):
        return {"value": str(value)}

    assert client.get("/items/").status_code == 404
