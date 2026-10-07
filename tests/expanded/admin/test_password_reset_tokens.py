"""Password reset tokens behavior and boundary cases."""

import pytest


@pytest.mark.parametrize("identifier", ["admin", "ADMIN", "admin@example.com", " ADMIN@EXAMPLE.COM "])
def test_username_and_email_resolve_same_reset_account(auth, identifier):
    token = auth.request_password_reset(identifier)
    assert token
    assert auth.reset_password(token, "Changed123!") is True
    assert auth.verify("admin", "Changed123!")


def test_reset_token_is_single_use(auth):
    token = auth.request_password_reset("admin")
    assert auth.reset_password(token, "Changed123!")
    assert not auth.reset_password(token, "Again123!")


def test_invalid_reset_does_not_change_password(auth):
    assert not auth.reset_password("unknown", "Changed123!")
    assert auth.verify("admin", "Admin123!")


def test_weak_password_preserves_reset_token(auth):
    token = auth.request_password_reset("admin")
    assert not auth.reset_password(token, "weak")
    assert auth.reset_password(token, "Changed123!")
