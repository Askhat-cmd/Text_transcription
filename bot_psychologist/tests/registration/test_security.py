from __future__ import annotations

from api.registration.security import (
    generate_access_key,
    generate_link_code,
    hash_key,
    verify_key,
)


def test_hash_key_returns_argon2_hash() -> None:
    hashed = hash_key("BP-TEST-KEY")
    assert hashed.startswith("$argon2")


def test_verify_key_true_for_correct_key() -> None:
    plain = "BP-TEST-KEY"
    hashed = hash_key(plain)
    assert verify_key(plain, hashed) is True


def test_verify_key_false_for_wrong_key() -> None:
    plain = "BP-TEST-KEY"
    hashed = hash_key(plain)
    assert verify_key("WRONG", hashed) is False


def test_generate_access_key_prefix() -> None:
    key = generate_access_key()
    assert key.startswith("BP-")


def test_generate_link_code_format() -> None:
    code = generate_link_code()
    assert len(code) == 6
    assert code.upper() == code
