"""Decimal precision behavior and boundary cases."""

from decimal import Decimal

import pytest

from flaxon.validation import DecimalField, FieldError


@pytest.mark.parametrize(
    "value, expected",
    [
        ("0", Decimal("0")),
        ("123.45", Decimal("123.45")),
        (12, Decimal("12")),
    ],
)
def test_valid_values(value, expected):
    assert DecimalField(places=2, minimum=Decimal("0")).deserialize(value) == expected


@pytest.mark.parametrize("value", ["-0.01", "1.234"])
def test_invalid_values(value):
    with pytest.raises(FieldError):
        DecimalField(places=2, minimum=Decimal("0")).deserialize(value)
