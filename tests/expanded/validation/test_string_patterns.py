"""String patterns behavior and boundary cases."""

import pytest

from flaxon.validation import FieldError, StrField


@pytest.mark.parametrize("value, expected", [("JM-123", "JM-123"), ("US-000", "US-000")])
def test_valid_values(value, expected):
    assert StrField(pattern=r"^[A-Z]{2}-[0-9]{3}$", strip=False).deserialize(value) == expected


@pytest.mark.parametrize("value", ["jm-123", "JM-123x", " JM-123", "<script>"])
def test_invalid_values(value):
    with pytest.raises(FieldError):
        StrField(pattern=r"^[A-Z]{2}-[0-9]{3}$", strip=False).deserialize(value)
