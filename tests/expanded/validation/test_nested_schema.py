"""Nested schema behavior and boundary cases."""

import pytest

from flaxon.validation import NestedField, Schema, StrField, ValidationError


class Address(Schema):
    city = StrField(required=True, min_length=2)


class Customer(Schema):
    address = NestedField(Address, required=True)


def test_nested_object_is_validated():
    value = Customer.load({"address": {"city": "Kingston"}})
    assert value.address.city == "Kingston"


@pytest.mark.parametrize("address", [None, "Kingston", [], {}])
def test_nested_errors_are_not_silently_accepted(address):
    with pytest.raises(ValidationError):
        Customer.load({"address": address})


def test_extra_nested_keys_are_not_attributes():
    value = Customer.load({"address": {"city": "Kingston", "admin": True}})
    assert not hasattr(value.address, "admin")
