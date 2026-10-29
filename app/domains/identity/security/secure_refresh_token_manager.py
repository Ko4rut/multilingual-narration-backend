"""Sinh Refresh Token và tạo hash an toàn để lưu trong database."""

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
        token = self.token_factory(self.token_bytes)
        if not token:
            raise ValueError("token_factory returned an empty refresh token")
        return IssuedRefreshToken(
            token=token,
            token_hash=self.hash_refresh_token(token),
        )

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        if not token:
            raise ValueError("refresh token must not be empty")
        return sha256(token.encode("utf-8")).hexdigest()
