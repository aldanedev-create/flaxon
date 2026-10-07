"""Schema request binding behavior and boundary cases."""

import pytest

from flaxon.validation import IntField, Schema, StrField


class Customer(Schema):
    name = StrField(required=True, min_length=2)
    age = IntField(required=True, minimum=13)


def test_valid_json_is_bound_to_schema(app, client):
    @app.post("/customers")
    async def create(data: Customer):
        return data.to_dict()

    response = client.post("/customers", json_data={"name": "Nova", "age": "18", "admin": True})
    assert response.status_code == 200
    assert response.json() == {"name": "Nova", "age": 18}


@pytest.mark.parametrize("payload", [{}, {"name": "N", "age": 12}, [], None])
def test_invalid_body_cannot_execute_handler(app, client, payload):
    called = []

    @app.post("/customers")
    async def create(data: Customer):
        called.append(data)
        return {"ok": True}

    response = client.post("/customers", json_data=payload)
    assert response.status_code == 422
    assert called == []
