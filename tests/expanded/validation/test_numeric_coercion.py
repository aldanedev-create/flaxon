"""Numeric coercion behavior and boundary cases."""

from decimal import Decimal

import pytest

from flaxon.validation.coercion import coerce_decimal, coerce_float, coerce_int


@pytest.mark.parametrize("raw,expected", [(" 123 ", 123), ("yes", 1), ("off", 0), (-5, -5)])
def test_integer_conversion(raw, expected):
    assert coerce_int(raw) == expected


@pytest.mark.parametrize("raw,expected", [("1.25", 1.25), (" -3.5 ", -3.5), (0, 0.0)])
def test_float_conversion(raw, expected):
    assert coerce_float(raw) == expected


def test_decimal_keeps_financial_precision():
    assert coerce_decimal("0.10") + coerce_decimal("0.20") == Decimal("0.30")


@pytest.mark.parametrize("raw", ["1.5", "x"])
def test_integer_rejects_invalid_text(raw):
    with pytest.raises(ValueError):
        coerce_int(raw)
