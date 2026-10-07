"""Email verification behavior and boundary cases."""


def test_verification_is_bound_to_issued_account(auth):
    token = auth.request_email_verification("admin")
    assert auth.verify_email(token)
    assert auth.users["admin"]["email_verified"] is True
    assert not auth.verify_email(token)


def test_unknown_token_cannot_verify_user(auth):
    assert not auth.verify_email("unknown")
    assert not auth.users["admin"].get("email_verified", False)


def test_account_without_email_cannot_issue_verification(auth):
    assert auth.request_email_verification("reader") is None


def test_verified_account_does_not_issue_another_token(auth):
    auth.users["admin"]["email_verified"] = True
    assert auth.request_email_verification("admin") is None
