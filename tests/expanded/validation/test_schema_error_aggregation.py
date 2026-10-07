"""Schema error aggregation behavior and boundary cases."""

import pytest

from flaxon.validation import IntField, Schema, StrField, ValidationError


class Quote(Schema):
    title = StrField(required=True, min_length=3)
    amount = IntField(required=True, minimum=1)


def test_multiple_errors_are_returned_together():
    with pytest.raises(ValidationError) as error:
        Quote.load({"title": "x", "amount": -1})
    assert set(error.value.fields) == {"title", "amount"}


@pytest.mark.parametrize("body", [None, [], "text", 12])
def test_non_object_bodies_produce_structured_validation_errors(body):
    with pytest.raises(ValidationError) as error:
        Quote.load(body)
    assert error.value.status_code == 422
    assert "body" in error.value.fields
