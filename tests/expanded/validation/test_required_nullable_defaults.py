"""Required nullable defaults behavior and boundary cases."""

import pytest

from flaxon.validation import IntField, Schema, StrField, ValidationError


class Options(Schema):
    name = StrField(required=True)
    count = IntField(default=5)
    note = StrField(nullable=True)


def test_default_and_nullable_fields():
    assert Options.load({"name": "task"}).to_dict() == {"name": "task", "count": 5, "note": None}


@pytest.mark.parametrize("data", [{}, {"name": None}])
def test_required_field_cannot_be_missing(data):
    with pytest.raises(ValidationError):
        Options.load(data)


def test_explicit_value_replaces_default():
    assert Options.load({"name": "task", "count": 0, "note": ""}).count == 0
