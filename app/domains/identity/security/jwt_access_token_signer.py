"""Ký và xác minh JWT Access Token cho domain Identity."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

import jwt
from jwt import PyJWTError

from app.domains.identity.exceptions import InvalidAccessToken
from app.domains.identity.utils.identity import required_text


# Thuật toán ký JWT: RS256 = RSA + SHA-256 (bất đối xứng).
JWT_ALGORITHM = "RS256"
# Giá trị trường "type" trong payload để phân biệt access token với các loại token khác (refresh token, reset password token, ...).
ACCESS_TOKEN_TYPE = "access"
# Danh sách các claim BẮT BUỘC phải có trong access token. Khi xác minh, nếu thiếu bất kỳ claim nào thì từ chối token (InvalidAccessToken).
REQUIRED_ACCESS_TOKEN_CLAIMS = (
    "iss",     # issuer: ai phát hành token (thường là URL của auth service)
    "aud",     # audience: token dành cho service nào (chống dùng token của service khác)
    "sub",     # subject: user_id — danh tính chủ thể sở hữu token
    "sid",     # session_id: liên kết token với một session trong DB → cho phép thu hồi token bằng cách revoke session
    "role_id", # role_id: vai trò của user, dùng cho RBAC mà không cần query DB
    "type",    # loại token, phải bằng ACCESS_TOKEN_TYPE ("access")
    "jti",     # JWT ID: định danh duy nhất của token → dùng cho blacklist/revocation, chống replay
    "iat",     # issued_at: thời điểm phát hành kiểm tra thủ công kèm leeway để test có thể inject clock
    "nbf",     # not_before: thời điểm token bắt đầu có hiệu lực kiểm tra thủ công kèm leeway (test clock)
    "exp",     # expires_at: thời điểm hết hạn kiểm tra thủ công kèm leeway (test clock)
)


@dataclass(frozen=True, slots=True)
class IssuedAccessToken:
    """JWT đã ký cùng thời điểm hết hạn để caller trả về client."""
    token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Các claim đã xác minh chữ ký và chuyển về kiểu dữ liệu nội bộ."""
    user_id: str
    session_id: str
    role_id: str
    token_id: str
    issued_at: datetime
    not_before: datetime
    expires_at: datetime


class JwtAccessTokenSigner:
    """Ký và xác minh Access Token bằng RS256.
    JWT chỉ được ký để chống chỉnh sửa, không được mã hóa. Payload tuyệt đối
    không chứa mật khẩu, password hash hoặc dữ liệu bí mật khác.
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
        """Ký Access Token ngắn hạn bằng private key RS256."""

        issued_at = self._aware_utc(self.clock())
        expires_at = issued_at + self.access_token_ttl
        payload = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": required_text(user_id, "user_id"),
            "sid": required_text(session_id, "session_id"),
            "role_id": required_text(role_id, "role_id"),
            "type": ACCESS_TOKEN_TYPE,
            "jti": required_text(self.token_id_factory(), "token_id"),
            "iat": int(issued_at.timestamp()),
            "nbf": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        }

        # Header kid cho phép verifier chọn đúng public key khi xoay khóa.
        token = jwt.encode(
            payload,
            self.private_key,
            algorithm=JWT_ALGORITHM,
            headers={"kid": self.active_key_id, "typ": "JWT"},
        )
        return IssuedAccessToken(token=token, expires_at=expires_at)

    def decode_access_token(self, token: str) -> AccessTokenClaims:
        """Xác minh chữ ký, issuer, audience, loại token và thời hạn."""

        try:
            # Header chưa xác minh chỉ được dùng để chọn public key. Payload chỉ
            # được tin cậy sau khi jwt.decode xác minh chữ ký bên dưới.
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
                    # Kiểm tra thời gian thủ công bằng clock inject để test ổn định.
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
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return value.astimezone(timezone.utc)
