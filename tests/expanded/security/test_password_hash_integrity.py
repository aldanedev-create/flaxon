"""Password hash integrity behavior and boundary cases."""

import pytest

from flaxon.security.password import PasswordHasher


def test_random_salts_produce_distinct_verifiable_hashes():
    hasher = PasswordHasher(iterations=1000)
    first = hasher.hash("Correct123!")
    second = hasher.hash("Correct123!")
    assert first != second
    assert hasher.verify("Correct123!", first)
    assert hasher.verify("Correct123!", second)
    assert not hasher.verify("Wrong123!", first)


@pytest.mark.parametrize(
    "hashed",
    ["", "not-a-hash", "other$1000$salt$hash", "pbkdf2_sha256$zero$salt$hash", "pbkdf2_sha256$1000$salt$é"],
)
def test_malformed_stored_hash_is_not_authentication(hashed):
    assert not PasswordHasher(iterations=1000).verify("password", hashed)


def test_iteration_upgrade_requires_rehash():
    hashed = PasswordHasher(algorithm="pbkdf2_sha256", iterations=1000).hash("Correct123!")
    assert PasswordHasher(algorithm="pbkdf2_sha256", iterations=2000).needs_rehash(hashed)
    assert not PasswordHasher(algorithm="pbkdf2_sha256", iterations=1000).needs_rehash(hashed)
