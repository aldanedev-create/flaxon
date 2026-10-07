"""Schema inheritance behavior and boundary cases."""

import pytest

from flaxon.validation import IntField, Schema, StrField, ValidationError


class Base(Schema):
    name = StrField(required=True)


class Child(Base):
    count = IntField(minimum=1, required=True)


def test_subclass_preserves_base_fields():
    assert Child.load({"name": "material", "count": "2"}).to_dict() == {"name": "material", "count": 2}


def test_child_does_not_modify_base_fields():
    assert Base.load({"name": "labour"}).to_dict() == {"name": "labour"}


def test_inherited_requirement_is_enforced():
    with pytest.raises(ValidationError) as error:
        Child.load({"count": 1})
    assert "name" in error.value.fields
