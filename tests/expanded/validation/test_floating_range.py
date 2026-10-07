"""Floating range behavior and boundary cases."""

import pytest

from flaxon.validation import FieldError, FloatField


@pytest.mark.parametrize("value, expected", [(-1.5, -1.5), (1.5, 1.5), (".25", 0.25), (0, 0.0)])
def test_valid_values(value, expected):
    assert FloatField(minimum=-1.5, maximum=1.5).deserialize(value) == expected


@pytest.mark.parametrize("value", [-1.51, 1.51, "bad", [], {}])
def test_invalid_values(value):
    with pytest.raises(FieldError):
        FloatField(minimum=-1.5, maximum=1.5).deserialize(value)
