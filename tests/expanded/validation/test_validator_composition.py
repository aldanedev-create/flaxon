"""Validator composition behavior and boundary cases."""

import pytest

from flaxon.validation import (
    FieldError,
    StrField,
    and_validators,
    length_validator,
    or_validators,
    pattern_validator,
)


@pytest.mark.parametrize("value", ["AB", "ABC", "ABCD"])
def test_and_requires_both_contracts(value):
    and_validators(length_validator(2, 4), pattern_validator(r"^[A-Z]+$"))(value, StrField())


@pytest.mark.parametrize("value", ["A", "abc", "ABCDE"])
def test_and_rejects_one_failed_contract(value):
    with pytest.raises(FieldError):
        and_validators(length_validator(2, 4), pattern_validator(r"^[A-Z]+$"))(value, StrField())


@pytest.mark.parametrize("value", ["AA", "123"])
def test_or_accepts_either_branch(value):
    or_validators(pattern_validator(r"^[A-Z]+$"), pattern_validator(r"^[0-9]+$"))(value, StrField())
