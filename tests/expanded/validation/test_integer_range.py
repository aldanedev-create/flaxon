"""Integer range behavior and boundary cases."""

import pytest

from flaxon.validation import FieldError, IntField


@pytest.mark.parametrize("value, expected", [(1, 1), (100, 100), ("42", 42), (" 7 ", 7)])
def test_valid_values(value, expected):
    assert IntField(minimum=1, maximum=100).deserialize(value) == expected


@pytest.mark.parametrize("value", [0, 101, "forty", [], {}])
def test_invalid_values(value):
    with pytest.raises(FieldError):
        IntField(minimum=1, maximum=100).deserialize(value)
