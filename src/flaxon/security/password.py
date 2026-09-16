from __future__ import annotations

import hashlib
import hmac
import secrets
import string


class PasswordHasher:
    def __init__(self, algorithm: str = "pbkdf2_sha256", iterations: int = 100000) -> None:
        self.algorithm = algorithm
        self.iterations = iterations
        self._argon2 = None
        if algorithm == "argon2":
            try:
                from argon2 import PasswordHasher as Argon2Hasher
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("PasswordHasher(algorithm='argon2') requires argon2-cffi.") from exc
            self._argon2 = Argon2Hasher()

    def hash(self, password: str) -> str:
        if self._argon2 is not None:
            return self._argon2.hash(password)
        salt = self._generate_salt()
        return self._hash_with_salt(password, salt)

    def verify(self, password: str, hashed: str) -> bool:
        if hashed.startswith("$argon2"):
            if self._argon2 is None:
                try:
                    from argon2 import PasswordHasher as Argon2Hasher
                    from argon2.exceptions import VerificationError
                except ImportError:
                    return False
                self._argon2 = Argon2Hasher()
            else:
                try:
                    from argon2.exceptions import VerificationError
                except ImportError:  # pragma: no cover - defensive
                    VerificationError = ValueError
            try:
                return bool(self._argon2.verify(hashed, password))
            except (VerificationError, ValueError, TypeError):
                return False
        try:
            algorithm, iterations, salt, hash_value = hashed.split("$")
            if algorithm != self.algorithm:
                return False
            iterations = int(iterations)
            new_hash = self._hash_raw(password, salt, iterations)
            return hmac.compare_digest(new_hash, hash_value)
        except ValueError:
            return False

    def needs_rehash(self, hashed: str) -> bool:
        if hashed.startswith("$argon2"):
            if self._argon2 is None:
                return self.algorithm != "argon2"
            return bool(self._argon2.check_needs_rehash(hashed))
        try:
            algorithm, iterations, salt, hash_value = hashed.split("$")
            return algorithm != self.algorithm or int(iterations) < self.iterations
        except ValueError:
            return True

    def _generate_salt(self, length: int = 22) -> str:
        alphabet = string.ascii_letters + string.digits + "./"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _hash_with_salt(self, password: str, salt: str) -> str:
        hash_value = self._hash_raw(password, salt, self.iterations)
        return f"{self.algorithm}${self.iterations}${salt}${hash_value}"

    def _hash_raw(self, password: str, salt: str, iterations: int) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()


class PasswordValidator:
    def __init__(
        self,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digits: bool = True,
        require_special: bool = True,
        max_length: int = 128,
    ) -> None:
        self.min_length = min_length
        self.max_length = max_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digits = require_digits
        self.require_special = require_special

    def validate(self, password: str) -> list[str]:
        errors = []

        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long.")

        if len(password) > self.max_length:
            errors.append(f"Password must be no more than {self.max_length} characters long.")

        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter.")

        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter.")

        if self.require_digits and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit.")

        # Treat any non-alphanumeric, non-whitespace symbol as special so
        # passwords generated with Unicode symbols are accepted consistently.
        if self.require_special and not any(not c.isalnum() and not c.isspace() for c in password):
            errors.append("Password must contain at least one special character.")

        common_passwords = {"password", "12345678", "qwerty", "letmein", "admin", "welcome"}
        if password.lower() in common_passwords:
            errors.append("Password is too common.")

        return errors

    def is_valid(self, password: str) -> bool:
        return len(self.validate(password)) == 0


def generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(alphabet) for _ in range(length))


_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hasher.verify(password, hashed)


def needs_rehash(hashed: str) -> bool:
    return _password_hasher.needs_rehash(hashed)
