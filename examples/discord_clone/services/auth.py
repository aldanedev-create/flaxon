"""Authentication and session helpers.

Passwords are hashed with Flaxon's maintained argon2 implementation
(`flaxon.security.password`). Sessions are signed-cookie dicts exposed as
`request.session`. We never store the password, and we never store the
session secret or bot tokens in the repository.
"""
from __future__ import annotations

from flaxon.exceptions import Unauthorized
from flaxon.security.password import hash_password, verify_password
from models import User

SESSION_KEY = "uid"
MIN_PASSWORD_LENGTH = 8
MAX_USERNAME_LENGTH = 40


def _validate_username(username: str) -> None:
    username = (username or "").strip()
    if not username:
        raise ValueError("username_required")
    if len(username) > MAX_USERNAME_LENGTH:
        raise ValueError("username_too_long")
    if not username.replace("_", "").replace("-", "").isalnum():
        raise ValueError("username_invalid")


async def register_user(username: str, email: str, password: str) -> User:
    _validate_username(username)
    email = (email or "").strip().lower()
    if "@" not in email or len(email) > 255:
        raise ValueError("email_invalid")
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValueError("password_too_short")
    if await User.exists(username=username):
        raise ValueError("username_taken")
    if await User.exists(email=email):
        raise ValueError("email_taken")
    return await User.create(
        username=username,
        email=email,
        display_name=username,
        password_hash=hash_password(password),
    )


async def authenticate(username: str, password: str) -> User | None:
    user = await User.get_or_none(username=username)
    # Constant-ish path: still hash even when the user is missing so timing
    # does not trivially reveal which usernames exist.
    if user is None or not user.password_hash:
        verify_password(password or "", "$argon2id$v=19$m=65536,t=3,p=4$0000000000000000$0000000000000000000000000000000000000000000")
        return None
    if not verify_password(password or "", user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def login_session(request, user: User) -> None:
    request.session[SESSION_KEY] = user.id


def logout_session(request) -> None:
    request.session.pop(SESSION_KEY, None)


async def current_user(request) -> User | None:
    uid = request.session.get(SESSION_KEY)
    if uid is None:
        return None
    return await User.get_or_none(id=uid, is_active=True)


async def require_user(request) -> User:
    user = await current_user(request)
    if user is None:
        raise Unauthorized("Authentication required")
    return user
