"""Datetime calendar behavior and boundary cases."""

from datetime import datetime

import pytest

from flaxon.validation import DateTimeField, FieldError


@pytest.mark.parametrize("value, expected", [("2026-10-07T23:59:59", datetime(2026, 10, 7, 23, 59, 59))])
def test_valid_values(value, expected):
    assert DateTimeField(required=True).deserialize(value) == expected


@pytest.mark.parametrize("value", [None, "2026-10-07T24:00:00", "2026-02-30T01:00:00", "yesterday", []])
def test_invalid_values(value):
    with pytest.raises(FieldError):
        DateTimeField(required=True).deserialize(value)
