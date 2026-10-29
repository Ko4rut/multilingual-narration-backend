"""Băm và xác minh mật khẩu cho domain Identity."""

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher


MAX_PASSWORD_LENGTH = 1024


class Argon2PasswordHasher:
    """Băm và xác minh mật khẩu bằng Argon2id."""

    def __init__(self, password_hash: PasswordHash | None = None):
        self._password_hash = password_hash or PasswordHash((Argon2Hasher(),))
        # Hash giả được dùng khi email không tồn tại. Việc vẫn chạy Argon2 giúp
        # giảm chênh lệch thời gian phản hồi giữa email đúng và email sai.
        self._dummy_hash = self._password_hash.hash("dummy-password-not-used")

    def hash_password(self, plain_password: str) -> str:
        """Tạo hash Argon2id có salt riêng để lưu thay cho mật khẩu gốc."""
        self._require_valid_password(plain_password)
        # Không strip mật khẩu vì khoảng trắng có thể là một phần mật khẩu mà
        # người dùng chủ động chọn. Argon2 tự sinh salt mới cho từng lần hash.
        return self._password_hash.hash(plain_password)

    def verify_password(self, plain_password: str, encoded_hash: str | None,) -> bool:
        """Đối chiếu mật khẩu nhập vào với hash đã lưu trong cơ sở dữ liệu."""

        if not plain_password or len(plain_password) > MAX_PASSWORD_LENGTH:
            return False

        # Không băm lại rồi so sánh hai chuỗi hash vì mỗi hash có salt riêng.
        # Hàm verify đọc salt/tham số từ encoded_hash và thực hiện đối chiếu.
        candidate_hash = encoded_hash or self._dummy_hash
        try:
            is_valid = self._password_hash.verify(
                plain_password,
                candidate_hash,
            )
        except (UnknownHashError, ValueError):
            # Hash hỏng hoặc không thuộc định dạng được hỗ trợ vẫn chạy một lần
            # verify giả trước khi trả False để tránh phản hồi quá nhanh.
            self._password_hash.verify(plain_password, self._dummy_hash)
            return False

        return encoded_hash is not None and is_valid

    @staticmethod
    def _require_valid_password(plain_password: str) -> None:
        if not plain_password:
            raise ValueError("password must not be empty")
        if len(plain_password) > MAX_PASSWORD_LENGTH:
            raise ValueError(
                f"password must not exceed {MAX_PASSWORD_LENGTH} characters"
            )
