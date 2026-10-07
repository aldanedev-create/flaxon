"""Trusted device ownership behavior and boundary cases."""

import hashlib

import pytest


def test_trusted_device_is_bound_to_account(auth):
    auth.users["admin"]["mfa_secret"] = auth.generate_mfa_secret()
    token = auth.issue_trusted_device("admin", "Laptop")
    assert auth.consume_trusted_device("admin", token)
    assert not auth.consume_trusted_device("reader", token)


def test_device_listing_does_not_disclose_credentials(auth):
    auth.users["admin"]["mfa_secret"] = auth.generate_mfa_secret()
    token = auth.issue_trusted_device("admin", "Laptop")
    listing = auth.list_trusted_devices("admin")
    assert listing[0]["label"] == "Laptop"
    assert "hash" not in listing[0]
    assert token not in str(listing)
    assert hashlib.sha256(token.encode()).hexdigest() not in str(listing)


def test_revoked_device_is_rejected(auth):
    auth.users["admin"]["mfa_secret"] = auth.generate_mfa_secret()
    token = auth.issue_trusted_device("admin", "Laptop")
    device = auth.list_trusted_devices("admin")[0]
    assert auth.revoke_trusted_device("admin", device["id"])
    assert not auth.consume_trusted_device("admin", token)


def test_device_requires_enabled_mfa(auth):
    with pytest.raises(ValueError):
        auth.issue_trusted_device("admin", "Laptop")
