"""Password policy behavior and boundary cases."""

import pytest

from flaxon.security.password import PasswordValidator


@pytest.mark.parametrize("password", ["Strong123!", "Unicode123§", "Aa1!" + "x" * 124])
def test_policy_accepts_valid_boundary_passwords(password):
    assert PasswordValidator().validate(password) == []


@pytest.mark.parametrize(
    "password,reason",
    [
        ("Aa1!", "at least"),
        ("a" * 129, "no more"),
        ("lowercase123!", "uppercase"),
        ("UPPERCASE123!", "lowercase"),
        ("NoDigitsHere!", "digit"),
        ("NoSymbol123 ", "special"),
        ("password", "common"),
    ],
)
def test_policy_reports_specific_failures(password, reason):
    assert any(reason in error for error in PasswordValidator().validate(password))


def test_relaxed_policy_still_rejects_common_passwords():
    policy = PasswordValidator(
        require_uppercase=False, require_lowercase=False, require_digits=False, require_special=False
    )
    assert not policy.is_valid("password")
    assert policy.is_valid("a long phrase")
