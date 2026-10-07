"""Response conversion behavior and boundary cases."""

import json

import pytest

from flaxon.http import HTMLResponse, JSONResponse, Response


@pytest.mark.parametrize("value", [{"ok": True}, [1, 2], ("a", "b")])
def test_container_response_is_json(value):
    response = Response.from_value(value)
    assert response.headers["content-type"].startswith("application/json")
    assert json.loads(response.body) == json.loads(json.dumps(value))


def test_none_response_is_no_content():
    response = Response.from_value(None)
    assert response.status_code == 204
    assert response.body == b""


def test_existing_response_retains_status_and_headers():
    original = HTMLResponse("<h1>hello</h1>", status_code=201, headers={"x-test": "value"})
    assert Response.from_value(original) is original
    assert original.headers["x-test"] == "value"


def test_unicode_response_length_counts_bytes():
    response = JSONResponse({"text": "日本"})
    assert int(response.headers["content-length"]) == len(response.body)
