from dataclasses import dataclass
from typing import Protocol

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher


MAX_PASSWORD_LENGTH = 1024


@dataclass(frozen=True, slots=True)
class PasswordVerification:
    """Kết quả xác minh và hash mới nếu hash hiện tại cần được nâng cấp."""

    is_valid: bool
    updated_hash: str | None = None


class PasswordProvider(Protocol):
    """Hợp đồng băm và xác minh mật khẩu để service không phụ thuộc thư viện."""

    def hash_password(self, plain_password: str) -> str: ...

    def verify_password(
        self,
        plain_password: str,
        encoded_hash: str | None,
    ) -> PasswordVerification: ...


class Argon2PasswordProvider:
    """Băm và xác minh mật khẩu bằng chính sách Argon2 của pwdlib."""

    def __init__(self, password_hash: PasswordHash | None = None):
        self._password_hash = password_hash or PasswordHash((Argon2Hasher(),))
        self._dummy_hash = self._password_hash.hash("dummy-password-not-used")

    def hash_password(self, plain_password: str) -> str:
        """Kiểm tra độ dài rồi tạo hash Argon2 để lưu vào cơ sở dữ liệu."""

        self._require_valid_length(plain_password)
        return self._password_hash.hash(plain_password)

    def verify_password(
        self,
        plain_password: str,
        encoded_hash: str | None,
    ) -> PasswordVerification:
        """Xác minh mật khẩu và đề xuất hash mới khi tham số Argon2 đã đổi."""

        if not plain_password or len(plain_password) > MAX_PASSWORD_LENGTH:
            return PasswordVerification(is_valid=False)

        # Luôn chạy Argon2 kể cả khi không tìm thấy tài khoản để hạn chế việc
        # suy đoán email hợp lệ dựa trên thời gian phản hồi.
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
