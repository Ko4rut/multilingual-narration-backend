import pytest
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.domains.identity.security.password import (
    MAX_PASSWORD_LENGTH,
    Argon2PasswordProvider,
)


def test_hash_and_verify_password_with_argon2id():
    provider = Argon2PasswordProvider()

    encoded_hash = provider.hash_password("correct horse battery staple")
    verification = provider.verify_password(
        "correct horse battery staple",
        encoded_hash,
    )

    assert encoded_hash.startswith("$argon2id$")
    assert verification.is_valid
    assert verification.updated_hash is None


def test_verify_password_rejects_wrong_missing_and_unknown_hashes():
    provider = Argon2PasswordProvider()
    encoded_hash = provider.hash_password("correct-password")

    assert not provider.verify_password("wrong-password", encoded_hash).is_valid
    assert not provider.verify_password("correct-password", None).is_valid
    assert not provider.verify_password("correct-password", "not-a-hash").is_valid


def test_verify_password_returns_rehash_when_argon2_policy_changes():
    old_password_hash = PasswordHash((Argon2Hasher(time_cost=2),))
    provider = Argon2PasswordProvider(PasswordHash((Argon2Hasher(time_cost=3),)))
    encoded_hash = old_password_hash.hash("correct-password")

    verification = provider.verify_password("correct-password", encoded_hash)

    assert verification.is_valid
    assert verification.updated_hash is not None
    assert provider.verify_password(
        "correct-password",
        verification.updated_hash,
    ).is_valid


@pytest.mark.parametrize(
    "password",
    ["", "a" * (MAX_PASSWORD_LENGTH + 1)],
)
def test_hash_password_rejects_invalid_lengths(password):
    provider = Argon2PasswordProvider()

    with pytest.raises(ValueError):
        provider.hash_password(password)
