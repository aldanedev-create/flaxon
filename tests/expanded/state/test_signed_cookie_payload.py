"""Signed cookie payload behavior and boundary cases."""

import pytest

from flaxon.sessions.backends.signed_cookie import SignedCookieBackend
from flaxon.sessions.session import Session


def test_roundtrip_preserves_decimal_timestamp_and_dots_in_data():
    backend = SignedCookieBackend("secret")
    session = Session(data={"email": "alice@example.com", "amount": 1.25})
    restored = backend.decode_session(backend.encode_session(session))
    assert restored is not None
    assert restored.id == session.id and restored.to_dict() == session.to_dict()
    assert restored.created_at == session.created_at


def test_modified_cookie_and_other_secret_are_rejected():
    backend = SignedCookieBackend("secret")
    cookie = backend.encode_session(Session(data={"role": "reader"}))
    assert backend.decode_session(cookie.replace("reader", "admin")) is None
    assert SignedCookieBackend("other").decode_session(cookie) is None


def test_expired_cookie_is_rejected(monkeypatch):
    monkeypatch.setattr("flaxon.sessions.backends.signed_cookie.time.time", lambda: 100)
    backend = SignedCookieBackend("secret")
    cookie = backend.encode_session(Session(ttl=2, created_at=100))
    monkeypatch.setattr("flaxon.sessions.backends.signed_cookie.time.time", lambda: 103)
    assert backend.decode_session(cookie) is None


@pytest.mark.parametrize("cookie", ["", "not-signed", "{}..", "{}.é"])
def test_malformed_cookie_returns_none(cookie):
    assert SignedCookieBackend("secret").decode_session(cookie) is None
