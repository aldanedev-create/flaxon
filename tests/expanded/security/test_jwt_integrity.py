"""Jwt integrity behavior and boundary cases."""

import pytest

from flaxon.exceptions import Unauthorized
from flaxon.security.jwt import JWT


def test_roundtrip_keeps_identity_and_nested_claims():
    jwt = JWT("secret-a")
    decoded = jwt.decode(jwt.encode({"sub": "alice", "scopes": ["read"], "profile": {"name": "Zoë"}}))
    assert decoded["sub"] == "alice"
    assert decoded["profile"] == {"name": "Zoë"}
    assert decoded["exp"] > decoded["iat"]


def test_other_secret_cannot_verify_token():
    with pytest.raises(Unauthorized):
        JWT("secret-b").decode(JWT("secret-a").encode({"sub": "alice"}))


@pytest.mark.parametrize("token", ["", "a", "a.b", "a.b.c.d", "a.b.c", "a.b.é"])
def test_malformed_tokens_fail_as_unauthorized(token):
    with pytest.raises(Unauthorized):
        JWT("secret").decode(token)


def test_expired_token_is_rejected(monkeypatch):
    monkeypatch.setattr("flaxon.security.jwt.time.time", lambda: 1000)
    jwt = JWT("secret")
    token = jwt.encode({"sub": "alice"}, expires_in=10)
    monkeypatch.setattr("flaxon.security.jwt.time.time", lambda: 1011)
    with pytest.raises(Unauthorized):
        jwt.decode(token)
