"""Session serialization behavior and boundary cases."""

from dataclasses import dataclass

import pytest

from flaxon.sessions.serializer import SessionSerializer
from flaxon.sessions.session import Session


@dataclass
class Profile:
    name: str
    age: int


def test_serializer_roundtrip_keeps_unicode_and_nested_data():
    serializer = SessionSerializer()
    data = {"profile": {"name": "Zoë"}, "flags": [True, False]}
    assert serializer.decode(serializer.encode(data)) == data


def test_dataclass_values_are_serialized_as_mappings():
    serializer = SessionSerializer()
    assert serializer.decode(serializer.encode({"profile": Profile("Alice", 30)})) == {
        "profile": {"name": "Alice", "age": 30}
    }


def test_invalid_json_returns_empty_mapping():
    assert SessionSerializer().decode("{broken") == {}


def test_unsupported_values_raise_instead_of_silently_stringifying():
    with pytest.raises(TypeError):
        SessionSerializer().encode({"unsupported": object()})


def test_session_serialization_keeps_application_data():
    serializer = SessionSerializer()
    session = Session(data={"user": 1})
    assert serializer.deserialize_session(serializer.serialize_session(session)) == {"user": 1}
