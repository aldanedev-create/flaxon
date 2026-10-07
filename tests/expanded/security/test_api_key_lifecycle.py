"""Api key lifecycle behavior and boundary cases."""

from flaxon.security.api_keys import APIKeyManager


def test_generated_key_hash_is_registered_without_raw_secret():
    manager = APIKeyManager()
    key, hashed = manager.generate_key("project")
    manager.register_hashed(hashed, {"scope": "read"})
    assert key.startswith("project_")
    assert manager.validate(key)["metadata"] == {"scope": "read"}
    assert key not in repr(manager.list_keys())
    assert hashed not in repr(manager.list_keys())


def test_revocation_and_deletion_remove_access():
    manager = APIKeyManager()
    manager.register("test-key")
    assert manager.validate("test-key") is not None
    manager.revoke("test-key")
    assert manager.validate("test-key") is None
    manager.delete("test-key")
    assert manager.list_keys() == []


def test_unknown_and_cross_manager_keys_are_invalid():
    first = APIKeyManager()
    first.register("only-first")
    assert first.validate("unknown") is None
    assert APIKeyManager().validate("only-first") is None
