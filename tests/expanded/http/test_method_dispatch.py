"""Method dispatch behavior and boundary cases."""

import pytest


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
def test_same_path_dispatches_by_method(app, client, method):
    for verb in ["get", "post", "put", "patch", "delete"]:

        def endpoint(verb=verb):
            return {"method": verb.upper()}

        getattr(app, verb)("/record")(endpoint)
    assert client.request(method, "/record").json() == {"method": method}


def test_disallowed_method_has_structured_405(app, client):
    @app.get("/read-only")
    async def endpoint():
        return {"ok": True}

    response = client.post("/read-only")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "FX-HTTP-405"


def test_unregistered_path_has_structured_404(client):
    response = client.get("/not-registered")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FX-HTTP-404"
