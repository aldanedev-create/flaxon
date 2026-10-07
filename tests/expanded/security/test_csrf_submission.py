"""Csrf submission behavior and boundary cases."""

import pytest

from flaxon.exceptions import Forbidden
from flaxon.http import Request
from flaxon.security.csrf import CSRF


async def receive():
    return {"type": "http.request", "body": b""}


def request(method, headers):
    return Request({"type": "http", "method": method, "path": "/", "headers": headers}, receive)


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS", "TRACE"])
def test_safe_methods_do_not_require_token(method):
    CSRF("secret").validate_request(request(method, []))


def test_cookie_alone_is_insufficient_for_mutation():
    csrf = CSRF("secret")
    token = csrf.generate_token()
    with pytest.raises(Forbidden):
        csrf.validate_request(request("POST", [(b"cookie", f"_csrf={token}".encode())]))


def test_explicit_header_allows_mutation():
    csrf = CSRF("secret")
    token = csrf.generate_token()
    csrf.validate_request(request("POST", [(b"x-csrf-token", token.encode())]))


def test_expired_and_future_tokens_are_invalid(monkeypatch):
    monkeypatch.setattr("flaxon.security.csrf.time.time", lambda: 1000)
    csrf = CSRF("secret")
    token = csrf.generate_token()
    monkeypatch.setattr("flaxon.security.csrf.time.time", lambda: 999)
    assert not csrf.verify_token(token)
    monkeypatch.setattr("flaxon.security.csrf.time.time", lambda: 4601)
    assert not csrf.verify_token(token)
