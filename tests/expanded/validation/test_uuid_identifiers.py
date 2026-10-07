"""Uuid identifiers behavior and boundary cases."""

from uuid import UUID

import pytest

from flaxon.validation import FieldError, UUIDField


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            "550e8400-e29b-41d4-a716-446655440000",
            UUID("550e8400-e29b-41d4-a716-446655440000"),
        )
    ],
)
def test_valid_values(value, expected):
    assert UUIDField(required=True).deserialize(value) == expected


@pytest.mark.parametrize("value", [None, "", "550e8400-e29b-41d4-a716-44665544000Z", 123, {}])
def test_invalid_values(value):
    with pytest.raises(FieldError):
        UUIDField(required=True).deserialize(value)
