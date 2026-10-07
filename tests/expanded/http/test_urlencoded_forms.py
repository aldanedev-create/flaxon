"""Urlencoded forms behavior and boundary cases."""

import pytest


@pytest.mark.parametrize(
    "body,expected", [("name=Nova+Coder", "Nova Coder"), ("name=%E6%97%A5%E6%9C%AC", "日本"), ("name=", "")]
)
def test_urlencoded_text_round_trips(app, client, body, expected):
    @app.post("/form")
    async def form(request):
        return (await request.form()).to_dict()

    result = client.post("/form", content=body, headers={"content-type": "application/x-www-form-urlencoded"})
    assert result.status_code == 200
    assert result.json()["name"] == expected


def test_repeated_checkboxes_are_retained(app, client):
    @app.post("/form")
    async def form(request):
        return (await request.form()).to_dict()

    result = client.post(
        "/form",
        content="service=steel&service=painting",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert result.json() == {"service": ["steel", "painting"]}
