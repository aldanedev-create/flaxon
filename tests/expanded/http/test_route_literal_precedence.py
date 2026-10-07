"""Route literal precedence behavior and boundary cases."""

import pytest


@pytest.mark.parametrize("literal_first", [True, False])
def test_literals_win_independently_of_registration_order(app, client, literal_first):
    async def detail(value):
        return {"kind": "detail", "value": value}

    async def creation():
        return {"kind": "create"}

    routes = [("/items/<value>", detail), ("/items/new", creation)]
    if literal_first:
        routes.reverse()
    for path, endpoint in routes:
        app.get(path)(endpoint)
    assert client.get("/items/new").json() == {"kind": "create"}
    assert client.get("/items/ordinary").json() == {"kind": "detail", "value": "ordinary"}


def test_literal_metacharacters_are_not_regular_expressions(app, client):
    @app.get("/files/report.json")
    async def endpoint():
        return {"ok": True}

    assert client.get("/files/report.json").status_code == 200
    assert client.get("/files/reportXjson").status_code == 404
