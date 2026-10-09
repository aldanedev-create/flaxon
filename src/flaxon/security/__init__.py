from __future__ import annotations

from .api_keys import APIKeyManager, api_key_required
from .authentication import (
    AuthenticationBackend,
    AuthenticationMiddleware,
    JWTBackend,
    SessionBackend,
    User,
    authenticate,
    get_current_user,
    login_required,
)
from .authorization import (
    AuthorizationChecker,
    AuthorizationMiddleware,
    authorize,
    has_permission,
    has_role,
    permission_required,
    role_required,
)
from .cors import CORSMiddleware
from .csrf import CSRF, CSRFMiddleware
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    DecryptionError,
    EncryptionError,
    PermissionDenied,
    RateLimitExceeded,
    SecurityError,
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
)
from .headers import SecurityHeaders, add_security_headers
from .jwt import JWT, create_jwt_token, jwt_required
from .oauth import OAuth2Backend, OAuth2Provider
from .password import (
    PasswordHasher,
    PasswordValidator,
    generate_password,
    hash_password,
    needs_rehash,
    verify_password,
)
from .permissions import (
    Permission,
    PermissionChecker,
    PermissionRegistry,
    permission_required as permission_required_decorator,
    register_permission,
)
from .rate_limit import DistributedRateLimiter, RateLimitMiddleware, RateLimiter
from .roles import Role, RoleChecker, RoleRegistry, register_role, role_required as role_required_decorator
from .sanitization import InputSanitizer, Sanitizer
from .secrets import (
    SecretManager,
    generate_hex_secret,
    generate_secret,
    generate_urlsafe_secret,
    get_required_secret,
    get_secret,
)
from .sessions import Session, SessionManager


def __getattr__(name: str) -> object:
    """Load optional cryptography-backed helpers only when requested."""
    if name in {"Encryptor", "Hasher"}:
        from .encryption import Encryptor, Hasher

        return {"Encryptor": Encryptor, "Hasher": Hasher}[name]
    raise AttributeError(f"module 'flaxon.security' has no attribute {name!r}")


__all__ = [
    "CSRF",
    "JWT",
    "APIKeyManager",
    "AuthenticationBackend",
    "AuthenticationError",
    "AuthenticationMiddleware",
    "AuthorizationChecker",
    "AuthorizationError",
    "AuthorizationMiddleware",
    "CORSMiddleware",
    "CSRFMiddleware",
    "DecryptionError",
    "DistributedRateLimiter",
    "EncryptionError",
    "Encryptor",
    "Hasher",
    "InputSanitizer",
    "JWTBackend",
    "OAuth2Backend",
    "OAuth2Provider",
    "PasswordHasher",
    "PasswordValidator",
    "Permission",
    "PermissionChecker",
    "PermissionDenied",
    "PermissionRegistry",
    "RateLimitExceeded",
    "RateLimitMiddleware",
    "RateLimiter",
    "Role",
    "RoleChecker",
    "RoleRegistry",
    "Sanitizer",
    "SecretManager",
    "SecurityError",
    "SecurityHeaders",
    "Session",
    "SessionBackend",
    "SessionManager",
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    "User",
    "add_security_headers",
    "api_key_required",
    "authenticate",
    "authorize",
    "create_jwt_token",
    "generate_hex_secret",
    "generate_password",
    "generate_secret",
    "generate_urlsafe_secret",
    "get_current_user",
    "get_required_secret",
    "get_secret",
    "has_permission",
    "has_role",
    "hash_password",
    "jwt_required",
    "login_required",
    "needs_rehash",
    "permission_required",
    "permission_required_decorator",
    "register_permission",
    "register_role",
    "role_required",
    "role_required_decorator",
    "verify_password",
]
