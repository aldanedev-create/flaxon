"""Route path parameters behavior and boundary cases."""

import pytest


@pytest.mark.parametrize("segment,expected", [("images/photo.png", "images/photo.png"), ("a/b/c", "a/b/c")])
def test_typed_route_values(app, client, segment, expected):
    @app.get("/items/<path:value>")
    async def endpoint(value):
        return {"value": str(value), "kind": type(value).__name__}

    response = client.get("/items/" + segment)
    assert response.status_code == 200
    assert response.json() == {"value": expected, "kind": "str"}


def test_missing_parameter_is_not_found(app, client):
    @app.get("/items/<path:value>")
    async def endpoint(value):
        return {"value": str(value)}

    assert client.get("/items/").status_code == 404
