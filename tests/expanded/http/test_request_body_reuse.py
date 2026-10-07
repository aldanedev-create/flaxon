"""Request body reuse behavior and boundary cases."""

import pytest


@pytest.mark.parametrize(
    "payload", [{"name": "日本語"}, {"nested": [1, 2, 3]}, ["a", "b"], {"enabled": False}]
)
def test_body_can_be_read_as_bytes_text_and_json(app, client, payload):
    @app.post("/echo")
    async def echo(request):
        first = await request.body()
        second = await request.body()
        return {"same": first == second, "text": await request.text(), "json": await request.json()}

    response = client.post("/echo", json_data=payload)
    assert response.status_code == 200
    assert response.json()["same"] is True
    assert response.json()["json"] == payload
    assert response.json()["text"]


def test_empty_json_body_is_none(app, client):
    @app.post("/echo")
    async def echo(request):
        return {"value": await request.json()}

    assert client.post("/echo").json() == {"value": None}
