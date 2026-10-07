"""Boolean inputs behavior and boundary cases."""

import pytest

from flaxon.validation import BoolField, FieldError


@pytest.mark.parametrize(
    "value, expected",
    [(" YES ", True), ("enabled", True), ("off", False), (" 0 ", False), (True, True), (False, False)],
)
def test_valid_values(value, expected):
    assert BoolField().deserialize(value) == expected


@pytest.mark.parametrize("value", ["maybe", [], {}, object()])
def test_invalid_values(value):
    with pytest.raises(FieldError):
        BoolField().deserialize(value)
