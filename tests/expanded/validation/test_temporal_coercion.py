"""Temporal coercion behavior and boundary cases."""

from datetime import date, datetime

import pytest

from flaxon.validation.coercion import coerce_date, coerce_datetime


@pytest.mark.parametrize("value", ["2024-02-29", "2024/02/29", "29-02-2024", "29/02/2024"])
def test_supported_date_formats(value):
    assert coerce_date(value) == date(2024, 2, 29)


@pytest.mark.parametrize("value", ["2026-10-07", "2026-10-07T00:00:00", "2026-10-07 00:00:00"])
def test_supported_datetime_formats(value):
    assert coerce_datetime(value) == datetime(2026, 10, 7)


@pytest.mark.parametrize("value", ["2026-02-29", "2026-13-01", "now"])
def test_invalid_calendar_dates(value):
    with pytest.raises(ValueError):
        coerce_date(value)
