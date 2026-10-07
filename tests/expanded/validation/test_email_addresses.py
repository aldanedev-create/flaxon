"""Email addresses behavior and boundary cases."""

import pytest

from flaxon.validation import EmailField, FieldError


@pytest.mark.parametrize(
    "value, expected",
    [("user@example.com", "user@example.com"), ("a+b@sub.example.org", "a+b@sub.example.org")],
)
def test_valid_values(value, expected):
    assert EmailField(required=True).deserialize(value) == expected


@pytest.mark.parametrize(
    "value", [None, "", "@example.com", "user@", "user@localhost", "user name@example.com", "a@@b.com"]
)
def test_invalid_values(value):
    with pytest.raises(FieldError):
        EmailField(required=True).deserialize(value)
