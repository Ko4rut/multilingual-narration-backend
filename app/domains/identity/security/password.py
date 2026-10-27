from dataclasses import dataclass
from typing import Protocol

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher


MAX_PASSWORD_LENGTH = 1024


@dataclass(frozen=True, slots=True)
class PasswordVerification:
    is_valid: bool
    updated_hash: str | None = None


class PasswordProvider(Protocol):
    def hash_password(self, plain_password: str) -> str: ...

    def verify_password(
        self,
        plain_password: str,
        encoded_hash: str | None,
    ) -> PasswordVerification: ...


class Argon2PasswordProvider:
    """Hash and verify passwords with pwdlib's recommended Argon2 policy."""

    def __init__(self, password_hash: PasswordHash | None = None):
        self._password_hash = password_hash or PasswordHash((Argon2Hasher(),))
        self._dummy_hash = self._password_hash.hash("dummy-password-not-used")

    def hash_password(self, plain_password: str) -> str:
        self._require_valid_length(plain_password)
        return self._password_hash.hash(plain_password)

    def verify_password(
        self,
        plain_password: str,
        encoded_hash: str | None,
    ) -> PasswordVerification:
        if not plain_password or len(plain_password) > MAX_PASSWORD_LENGTH:
            return PasswordVerification(is_valid=False)

        candidate_hash = encoded_hash or self._dummy_hash
        try:
            is_valid, updated_hash = self._password_hash.verify_and_update(
                plain_password,
                candidate_hash,
            )
        except (UnknownHashError, ValueError):
            self._password_hash.verify(plain_password, self._dummy_hash)
            return PasswordVerification(is_valid=False)

        if encoded_hash is None:
            return PasswordVerification(is_valid=False)
        return PasswordVerification(
            is_valid=is_valid,
            updated_hash=updated_hash if is_valid else None,
        )

    @staticmethod
    def _require_valid_length(plain_password: str) -> None:
        if not plain_password:
            raise ValueError("password must not be empty")
        if len(plain_password) > MAX_PASSWORD_LENGTH:
            raise ValueError(
                f"password must not exceed {MAX_PASSWORD_LENGTH} characters"
            )
