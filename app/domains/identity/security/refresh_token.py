from collections.abc import Callable
from dataclasses import dataclass, field
from hashlib import sha256
from secrets import token_urlsafe
from typing import Protocol


MINIMUM_REFRESH_TOKEN_BYTES = 32


@dataclass(frozen=True, slots=True)
class IssuedRefreshToken:
    """Refresh Token thô để gửi một lần và SHA-256 hash để lưu trữ."""

    token: str = field(repr=False)
    token_hash: str


class RefreshTokenProvider(Protocol):
    """Hợp đồng sinh Refresh Token và chuyển token thô thành hash."""

    def issue_refresh_token(self) -> IssuedRefreshToken: ...

    def hash_refresh_token(self, token: str) -> str: ...


class SecureRefreshTokenProvider:
    """Sinh Refresh Token opaque và chỉ cung cấp SHA-256 hash để lưu trữ."""

    def __init__(
        self,
        *,
        token_bytes: int = MINIMUM_REFRESH_TOKEN_BYTES,
        token_factory: Callable[[int], str] = token_urlsafe,
    ):
        if token_bytes < MINIMUM_REFRESH_TOKEN_BYTES:
            raise ValueError(
                f"token_bytes must be at least {MINIMUM_REFRESH_TOKEN_BYTES}"
            )
        self.token_bytes = token_bytes
        self.token_factory = token_factory

    def issue_refresh_token(self) -> IssuedRefreshToken:
        """Sinh token đủ entropy; token thô không được ghi vào cơ sở dữ liệu."""

        token = self.token_factory(self.token_bytes)
        if not token:
            raise ValueError("token_factory returned an empty refresh token")
        return IssuedRefreshToken(
            token=token,
            token_hash=self.hash_refresh_token(token),
        )

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        """Băm token để tra cứu phiên mà không lưu thông tin xác thực gốc."""

        if not token:
            raise ValueError("refresh token must not be empty")
        return sha256(token.encode("utf-8")).hexdigest()
