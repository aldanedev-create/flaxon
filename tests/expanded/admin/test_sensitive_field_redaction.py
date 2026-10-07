"""Sensitive field redaction behavior and boundary cases."""

import pytest


@pytest.mark.parametrize(
    "name",
    [
        "password",
        "password_hash",
        "mfa_secret",
        "mfa_pending_secret",
        "mfa_pending_recovery_codes",
        "mfa_recovery_codes",
        "trusted_devices",
    ],
)
def test_authentication_secrets_are_never_public(auth, name):
    record = {"username": "admin", name: "secret", "email": "admin@example.com"}
    public = auth.public(record)
    assert name not in public
    assert public["email"] == "admin@example.com"


def test_public_projection_does_not_mutate_record(auth):
    before = dict(auth.users["admin"])
    auth.public(auth.users["admin"])
    assert auth.users["admin"] == before
