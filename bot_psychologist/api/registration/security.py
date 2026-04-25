"""Security helpers for registration module."""

from __future__ import annotations

import secrets
import string
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, VerifyMismatchError


_KEY_ALPHABET = string.ascii_uppercase + string.digits
_ACCESS_ALPHABET = string.ascii_uppercase + string.digits
_hasher = PasswordHasher()


def hash_key(plain_key: str) -> str:
    """Hash access key with argon2."""
    return _hasher.hash(plain_key)


def verify_key(plain_key: str, hashed_key: str) -> bool:
    """Verify access key against argon2 hash."""
    try:
        return bool(_hasher.verify(hashed_key, plain_key))
    except (VerifyMismatchError, Argon2Error, ValueError, TypeError):
        return False


def generate_access_key(prefix: str = "BP") -> str:
    """Generate high-entropy access key."""
    token = "".join(secrets.choice(_ACCESS_ALPHABET) for _ in range(24))
    return f"{prefix}-{token}"


def generate_invite_key(prefix: str = "BP-INVITE") -> str:
    """Generate invite key."""
    token = "".join(secrets.choice(_KEY_ALPHABET) for _ in range(18))
    return f"{prefix}-{token}"


def generate_link_code(length: int = 6) -> str:
    """Generate short uppercase linking code."""
    return "".join(secrets.choice(_KEY_ALPHABET) for _ in range(length))

