"""Credential login behavior and boundary cases."""

import asyncio

import pytest


@pytest.mark.parametrize(
    "username,password", [("admin", "wrong"), ("unknown", "Admin123!"), ("Admin", "Admin123!"), ("admin", "")]
)
def test_invalid_credentials_never_create_session(auth, username, password):
    assert asyncio.run(auth.login(username, password)) is None
    assert auth.backend.sessions == {}


def test_valid_login_has_only_public_account_data(auth):
    token = asyncio.run(auth.login("admin", "Admin123!"))
    user = asyncio.run(auth.backend.validate_token(token))
    assert user.username == "admin"
    assert "password_hash" not in user.to_dict()


def test_inactive_user_cannot_login(auth):
    auth.users["admin"]["active"] = False
    assert asyncio.run(auth.login("admin", "Admin123!")) is None
