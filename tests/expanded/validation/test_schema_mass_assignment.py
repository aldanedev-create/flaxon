"""Schema mass assignment behavior and boundary cases."""

from flaxon.validation import Schema, StrField


class Profile(Schema):
    name = StrField(required=True)


def test_undeclared_privileges_are_discarded():
    profile = Profile.load({"name": "Nova", "roles": ["admin"], "password_hash": "fake"})
    assert profile.to_dict() == {"name": "Nova"}
    assert not hasattr(profile, "roles")


def test_dunder_keys_cannot_replace_schema_methods():
    profile = Profile.load({"name": "Nova", "to_dict": "replacement", "__class__": "fake"})
    assert profile.to_dict() == {"name": "Nova"}
