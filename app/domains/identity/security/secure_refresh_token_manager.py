"""Sinh refresh token ngẫu nhiên và tạo hash dùng để lưu trong database.

Refresh token ở đây là một chuỗi opaque: bản thân chuỗi không chứa thông tin
người dùng. Mỗi lần cấp token, module trả về hai giá trị:

- token gốc để tầng HTTP gửi cho client qua cookie bảo mật;
- SHA-256 hash để ``AuthenticationService`` lưu và tra cứu phiên đăng nhập.

Module không tự lưu phiên, đặt cookie hay thu hồi token. Những thao tác đó lần
lượt thuộc về service, repository và router. Không lưu token gốc giúp hạn chế
việc token bị sử dụng trực tiếp nếu dữ liệu phiên trong database bị lộ.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from hashlib import sha256
from secrets import token_urlsafe


@dataclass(frozen=True, slots=True)
class IssuedRefreshToken:
    """Refresh Token thô để gửi một lần và SHA-256 hash để lưu database."""
    token: str = field(repr=False)
    token_hash: str


class SecureRefreshTokenManager:
    """Sinh opaque Refresh Token và không lưu token gốc trong database."""
    def __init__(
        self,
        *,
        token_bytes: int = 48,
        token_factory: Callable[[int], str] = token_urlsafe,
    ):
        if token_bytes < 32:
            raise ValueError("token_bytes must be at least 32")
        self.token_bytes = token_bytes
        self.token_factory = token_factory

    def issue_refresh_token(self) -> IssuedRefreshToken:
        # Sinh refresh token ngẫu nhiên và hash SHA-256 để lưu trong database.
        token = self.token_factory(self.token_bytes)
        if not token:
            raise ValueError("token_factory returned an empty refresh token")
        return IssuedRefreshToken(
            token=token,
            token_hash=self.hash_refresh_token(token),
        )

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        # Mã hóa SHA-256 của refresh token để lưu trong database. Không lưu token gốc.
        if not token:
            raise ValueError("refresh token must not be empty")
        return sha256(token.encode("utf-8")).hexdigest()
