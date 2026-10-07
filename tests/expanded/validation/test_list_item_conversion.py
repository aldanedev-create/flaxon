"""List item conversion behavior and boundary cases."""

import pytest

from flaxon.validation import FieldError, IntField, ListField


@pytest.mark.parametrize("value, expected", [(["1", "2"], [1, 2]), ([3], [3]), ([1, 2, 3], [1, 2, 3])])
def test_valid_values(value, expected):
    assert ListField(IntField(minimum=1), min_items=1, max_items=3).deserialize(value) == expected


@pytest.mark.parametrize("value", [[], [0], [1, 2, 3, 4], "1,2", ["bad"]])
def test_invalid_values(value):
    with pytest.raises(FieldError):
        ListField(IntField(minimum=1), min_items=1, max_items=3).deserialize(value)
