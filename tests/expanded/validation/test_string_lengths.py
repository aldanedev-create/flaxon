"""String lengths behavior and boundary cases."""

import pytest

from flaxon.validation import FieldError, StrField


@pytest.mark.parametrize(
    "value, expected", [("ab", "ab"), ("abcdefgh", "abcdefgh"), ("  Nova  ", "Nova"), ("日本語", "日本語")]
)
def test_valid_values(value, expected):
    assert StrField(min_length=2, max_length=8).deserialize(value) == expected


@pytest.mark.parametrize("value", ["", "x", "abcdefghi", 123, [], {}])
def test_invalid_values(value):
    with pytest.raises(FieldError):
        StrField(min_length=2, max_length=8).deserialize(value)
