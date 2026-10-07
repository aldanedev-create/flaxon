"""Choice membership behavior and boundary cases."""

import pytest

from flaxon.validation import ChoiceField, FieldError


@pytest.mark.parametrize("value, expected", [("draft", "draft"), ("paid", "paid")])
def test_valid_values(value, expected):
    assert ChoiceField(["draft", "approved", "paid"], required=True).deserialize(value) == expected


@pytest.mark.parametrize("value", [None, "Draft", "deleted", "", 0])
def test_invalid_values(value):
    with pytest.raises(FieldError):
        ChoiceField(["draft", "approved", "paid"], required=True).deserialize(value)
