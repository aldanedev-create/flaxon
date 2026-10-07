"""Date calendar behavior and boundary cases."""

from datetime import date

import pytest

from flaxon.validation import DateField, FieldError


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2024-02-29", date(2024, 2, 29)),
        ("2026-12-31", date(2026, 12, 31)),
    ],
)
def test_valid_values(value, expected):
    assert DateField(required=True).deserialize(value) == expected


@pytest.mark.parametrize("value", [None, "2026-02-29", "2026-13-01", "2026-00-01", "not-date", 42])
def test_invalid_values(value):
    with pytest.raises(FieldError):
        DateField(required=True).deserialize(value)
