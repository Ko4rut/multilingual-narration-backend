from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from typing import Protocol

import jwt
from jwt import PyJWTError

from app.domains.identity.exceptions import InvalidAccessToken


JWT_ALGORITHM = "RS256"
ACCESS_TOKEN_TYPE = "access"
REQUIRED_ACCESS_TOKEN_CLAIMS = (
    "iss",
    "aud",
    "sub",
    "sid",
    "role_id",
    "type",
    "jti",
    "iat",
    "nbf",
    "exp",
)


@dataclass(frozen=True, slots=True)
class IssuedAccessToken:
    """JWT đã ký cùng thời điểm hết hạn phục vụ HTTP response."""

    token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Các claim đã được xác minh và chuyển về kiểu dữ liệu nội bộ."""

    user_id: str
    session_id: str
    role_id: str
    token_id: str
    issued_at: datetime
    not_before: datetime
    expires_at: datetime


class AccessTokenProvider(Protocol):
    """Hợp đồng cấp và xác thực Access Token cho tầng service."""

    def issue_access_token(
        self,
        *,
        user_id: str,
        session_id: str,
        role_id: str,
    ) -> IssuedAccessToken: ...

    def decode_access_token(self, token: str) -> AccessTokenClaims: ...


class JwtAccessTokenProvider:
    """Cấp và xác minh JWT ký RS256 với lựa chọn khóa rõ ràng bằng ``kid``.

    JWT chỉ được ký để chống sửa đổi, không được mã hóa; vì vậy payload không
    được chứa mật khẩu, Refresh Token hoặc dữ liệu bí mật.
    """

    def __init__(
        self,
        *,
        private_key: str,
        public_keys: Mapping[str, str],
        active_key_id: str,
        issuer: str,
        audience: str,
        access_token_ttl: timedelta = timedelta(minutes=15),
        leeway: timedelta = timedelta(seconds=30),
        clock: Callable[[], datetime] | None = None,
        token_id_factory: Callable[[], str] | None = None,
    ):
        if not private_key.strip():
            raise ValueError("private_key must not be empty")
        if active_key_id not in public_keys:
            raise ValueError("active_key_id must exist in public_keys")
        if not issuer.strip():
            raise ValueError("issuer must not be empty")
        if not audience.strip():
            raise ValueError("audience must not be empty")
        if access_token_ttl <= timedelta(0):
            raise ValueError("access_token_ttl must be positive")
        if leeway < timedelta(0):
            raise ValueError("leeway must not be negative")

        self.private_key = private_key
        self.public_keys = dict(public_keys)
        self.active_key_id = active_key_id
        self.issuer = issuer
        self.audience = audience
        self.access_token_ttl = access_token_ttl
        self.leeway = leeway
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.token_id_factory = token_id_factory or (lambda: token_urlsafe(24))

    def issue_access_token(
        self,
        *,
        user_id: str,
        session_id: str,
        role_id: str,
    ) -> IssuedAccessToken:
        """Tạo Access Token ngắn hạn gắn với người dùng, vai trò và phiên."""

        issued_at = self._aware_utc(self.clock())
        expires_at = issued_at + self.access_token_ttl
        payload = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": self._required_text(user_id, "user_id"),
            "sid": self._required_text(session_id, "session_id"),
            "role_id": self._required_text(role_id, "role_id"),
            "type": ACCESS_TOKEN_TYPE,
            "jti": self._required_text(self.token_id_factory(), "token_id"),
            "iat": int(issued_at.timestamp()),
            "nbf": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(
            payload,
            self.private_key,
            algorithm=JWT_ALGORITHM,
            headers={"kid": self.active_key_id, "typ": "JWT"},
        )
        return IssuedAccessToken(token=token, expires_at=expires_at)

    def decode_access_token(self, token: str) -> AccessTokenClaims:
        """Xác minh chữ ký, issuer, audience, loại token và các mốc thời gian."""

        try:
            # Header chưa xác minh chỉ được dùng để chọn public key. Mọi claim
            # chỉ được tin cậy sau khi jwt.decode xác minh chữ ký bên dưới.
            header = jwt.get_unverified_header(token)
            if header.get("alg") != JWT_ALGORITHM:
                raise InvalidAccessToken("Access token algorithm is not allowed")
            key_id = header.get("kid")
            if not isinstance(key_id, str) or key_id not in self.public_keys:
                raise InvalidAccessToken("Access token key is not recognized")

            payload = jwt.decode(
                token,
                self.public_keys[key_id],
                algorithms=[JWT_ALGORITHM],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "require": list(REQUIRED_ACCESS_TOKEN_CLAIMS),
                    # Các mốc thời gian được kiểm tra thủ công bằng clock được
                    # inject để kiểm thử tất định và vẫn áp dụng leeway.
                    "verify_exp": False,
                    "verify_iat": False,
                    "verify_nbf": False,
                },
            )
            return self._claims_from_payload(payload)
        except InvalidAccessToken:
            raise
        except (PyJWTError, TypeError, ValueError) as exc:
            raise InvalidAccessToken("Access token is invalid") from exc

    def _claims_from_payload(self, payload: dict[str, object]) -> AccessTokenClaims:
        if payload.get("type") != ACCESS_TOKEN_TYPE:
            raise InvalidAccessToken("Access token type is invalid")

        issued_at = self._timestamp_claim(payload, "iat")
        not_before = self._timestamp_claim(payload, "nbf")
        expires_at = self._timestamp_claim(payload, "exp")
        now = self._aware_utc(self.clock())
        if issued_at > now + self.leeway:
            raise InvalidAccessToken("Access token was issued in the future")
        if not_before > now + self.leeway:
            raise InvalidAccessToken("Access token is not active yet")
        if expires_at <= now - self.leeway:
            raise InvalidAccessToken("Access token has expired")
        if expires_at <= issued_at:
            raise InvalidAccessToken("Access token timestamps are invalid")

        return AccessTokenClaims(
            user_id=self._string_claim(payload, "sub"),
            session_id=self._string_claim(payload, "sid"),
            role_id=self._string_claim(payload, "role_id"),
            token_id=self._string_claim(payload, "jti"),
            issued_at=issued_at,
            not_before=not_before,
            expires_at=expires_at,
        )

    @staticmethod
    def _timestamp_claim(payload: dict[str, object], name: str) -> datetime:
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidAccessToken(f"Access token claim '{name}' is invalid")
        return datetime.fromtimestamp(value, timezone.utc)

    @staticmethod
    def _string_claim(payload: dict[str, object], name: str) -> str:
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            raise InvalidAccessToken(f"Access token claim '{name}' is invalid")
        return value

    @staticmethod
    def _required_text(value: str, field_name: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(f"{field_name} must not be empty")
        return normalized_value

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return value.astimezone(timezone.utc)
