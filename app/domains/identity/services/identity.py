from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re
from secrets import token_urlsafe

import jwt
from jwt import PyJWTError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.identity.exceptions import (
    InactiveManagerUser,
    InvalidAccessToken,
    InvalidCredentials,
    ManagerUserEmailAlreadyExists,
    ManagerUserNotFound,
    PermissionNotFound,
    RefreshTokenAlreadyExists,
    RoleNameAlreadyExists,
    RoleNotFound,
    UserSessionExpired,
    UserSessionNotFound,
    UserSessionRevoked,
)
from app.domains.identity.models.manager_user import (
    ManagerUserModel,
    ManagerUserStatus,
)
from app.domains.identity.models.permission import PermissionModel
from app.domains.identity.models.role import RoleModel
from app.domains.identity.models.user_session import UserSessionModel
from app.domains.identity.repositories.manager_user import ManagerUserRepository
from app.domains.identity.repositories.permission import PermissionRepository
from app.domains.identity.repositories.role import RoleRepository
from app.domains.identity.repositories.role_permission import RolePermissionRepository
from app.domains.identity.repositories.user_session import UserSessionRepository
from app.domains.identity.models.role_permission import RolePermissionModel
from app.domains.identity.utils.identity import (
    generate_dated_identifier,
    generate_reference_identifier,
    utc_now,
)


ACTIVE_USER_STATUS = ManagerUserStatus.ACTIVE
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_PASSWORD_LENGTH = 1024
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
    """JWT đã ký cùng thời điểm hết hạn để caller trả về client sau này."""

    token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Các claim đã được xác minh chữ ký và chuyển về kiểu nội bộ."""

    user_id: str
    session_id: str
    role_id: str
    token_id: str
    issued_at: datetime
    not_before: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class CredentialLoginResult:
    """Kết quả đăng nhập; Refresh Token thô chỉ được gửi qua cookie."""

    manager_user: ManagerUserModel
    user_session: UserSessionModel
    access_token: IssuedAccessToken
    refresh_token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class RefreshResult:
    """Kết quả xoay Refresh Token và cấp Access Token mới."""

    user_session: UserSessionModel
    access_token: IssuedAccessToken
    refresh_token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    """Tài khoản và claim đã được xác minh từ một Bearer Access Token."""

    manager_user: ManagerUserModel
    user_session: UserSessionModel
    claims: AccessTokenClaims


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


class Argon2PasswordHasher:
    """Băm và xác minh mật khẩu bằng Argon2id ngay trong service Identity."""

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

    def verify_password(
        self,
        plain_password: str,
        encoded_hash: str | None,
    ) -> bool:
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


class JwtAccessTokenSigner:
    """Ký và xác minh Access Token RS256 ngay trong service Identity.

    JWT chỉ được ký để chống chỉnh sửa, không được mã hóa. Vì vậy payload tuyệt
    đối không chứa mật khẩu, password hash hoặc dữ liệu bí mật khác.
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
            "sub": self._required_text(user_id, "user_id"),
            "sid": self._required_text(session_id, "session_id"),
            "role_id": self._required_text(role_id, "role_id"),
            "type": ACCESS_TOKEN_TYPE,
            "jti": self._required_text(self.token_id_factory(), "token_id"),
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


class IdentityService:
    """Điều phối đăng nhập, vòng đời phiên và kiểm tra quyền RBAC."""

    def __init__(
        self,
        session: Session,
        manager_user_repository: ManagerUserRepository,
        user_session_repository: UserSessionRepository,
        permission_repository: PermissionRepository,
        password_hasher: Argon2PasswordHasher,
        access_token_signer: JwtAccessTokenSigner,
        refresh_token_manager: SecureRefreshTokenManager,
        *,
        refresh_token_ttl: timedelta = timedelta(days=30),
        clock: Callable[[], datetime] = utc_now,
        id_factory: Callable[[str, datetime], str] = generate_dated_identifier,
    ):
        if refresh_token_ttl <= timedelta(0):
            raise ValueError("refresh_token_ttl must be positive")
        self.session = session
        self.manager_user_repository = manager_user_repository
        self.user_session_repository = user_session_repository
        self.permission_repository = permission_repository
        self.password_hasher = password_hasher
        self.access_token_signer = access_token_signer
        self.refresh_token_manager = refresh_token_manager
        self.refresh_token_ttl = refresh_token_ttl
        self.clock = clock
        self.id_factory = id_factory

    def authenticate_credentials(
        self,
        *,
        email: str,
        password: str,
    ) -> ManagerUserModel:
        """Xác minh email/mật khẩu nhưng chưa tạo session hoặc token."""

        normalized_email = self._normalize_email(email)
        manager_user = self.manager_user_repository.get_by_email(normalized_email)

        # Vẫn gọi verify khi không tìm thấy email. Password hasher sẽ dùng dummy
        # hash để hạn chế việc dò tài khoản dựa trên thời gian phản hồi.
        is_valid_password = self.password_hasher.verify_password(
            password,
            manager_user.password_hash if manager_user is not None else None,
        )
        if manager_user is None or not is_valid_password:
            raise InvalidCredentials("Invalid email or password")
        if manager_user.user_status != ACTIVE_USER_STATUS:
            raise InactiveManagerUser("Manager user is inactive")
        return manager_user

    def authenticate_and_issue_access_token(
        self,
        *,
        email: str,
        password: str,
    ) -> CredentialLoginResult:
        """Xác minh credential, tạo session rồi cấp cặp token."""

        created_at = self.clock()
        try:
            with self.session.begin():
                manager_user = self.authenticate_credentials(
                    email=email,
                    password=password,
                )
                issued_refresh_token = (
                    self.refresh_token_manager.issue_refresh_token()
                )
                user_session = UserSessionModel(
                    id=self.id_factory("sess", created_at),
                    user_id=manager_user.id,
                    refresh_token_hash=issued_refresh_token.token_hash,
                    expires_at=created_at + self.refresh_token_ttl,
                    created_at=created_at,
                    revoked_at=None,
                )
                manager_user.last_login_at = created_at
                self.user_session_repository.add(user_session)
                self.session.flush()
                access_token = self.access_token_signer.issue_access_token(
                    user_id=manager_user.id,
                    session_id=user_session.id,
                    role_id=manager_user.role_id,
                )
        except IntegrityError as exc:
            self._translate_session_integrity_error(exc)

        return CredentialLoginResult(
            manager_user=manager_user,
            user_session=user_session,
            access_token=access_token,
            refresh_token=issued_refresh_token.token,
        )

    def authenticate_access_token(self, token: str) -> AuthenticatedIdentity:
        """Xác minh JWT và đối chiếu lại tài khoản hiện tại trong database."""

        claims = self.access_token_signer.decode_access_token(token)
        user_session = self.user_session_repository.get_by_id(claims.session_id)
        if user_session is None or user_session.user_id != claims.user_id:
            raise UserSessionNotFound("User session not found")
        self._require_usable_session(user_session, self.clock())
        manager_user = self._require_manager_user(claims.user_id)
        if manager_user.user_status != ACTIVE_USER_STATUS:
            raise InactiveManagerUser("Manager user is inactive")
        if manager_user.role_id != claims.role_id:
            # Token mang role cũ không được tiếp tục sử dụng sau khi đổi role.
            raise InvalidAccessToken("Access token role is no longer current")
        return AuthenticatedIdentity(
            manager_user=manager_user,
            user_session=user_session,
            claims=claims,
        )

    def refresh(self, refresh_token: str) -> RefreshResult:
        """Khóa session, xoay Refresh Token và cấp Access Token mới."""

        token_hash = self.refresh_token_manager.hash_refresh_token(refresh_token)
        now = self.clock()
        try:
            with self.session.begin():
                user_session = (
                    self.user_session_repository.get_by_refresh_token_hash_for_update(
                        token_hash
                    )
                )
                if user_session is None:
                    raise UserSessionNotFound("User session not found")
                self._require_usable_session(user_session, now)
                manager_user = self._require_manager_user(user_session.user_id)
                if manager_user.user_status != ACTIVE_USER_STATUS:
                    raise InactiveManagerUser("Manager user is inactive")

                issued_refresh_token = (
                    self.refresh_token_manager.issue_refresh_token()
                )
                user_session.refresh_token_hash = issued_refresh_token.token_hash
                self.session.flush()
                access_token = self.access_token_signer.issue_access_token(
                    user_id=manager_user.id,
                    session_id=user_session.id,
                    role_id=manager_user.role_id,
                )
        except IntegrityError as exc:
            self._translate_session_integrity_error(exc)

        return RefreshResult(
            user_session=user_session,
            access_token=access_token,
            refresh_token=issued_refresh_token.token,
        )

    def logout(self, refresh_token: str) -> UserSessionModel:
        """Thu hồi đúng session sở hữu Refresh Token được gửi lên."""

        token_hash = self.refresh_token_manager.hash_refresh_token(refresh_token)
        revoked_at = self.clock()
        with self.session.begin():
            user_session = (
                self.user_session_repository.get_by_refresh_token_hash_for_update(
                    token_hash
                )
            )
            if user_session is None:
                raise UserSessionNotFound("User session not found")
            if user_session.revoked_at is None:
                user_session.revoked_at = revoked_at
                self.session.flush()
        return user_session

    def has_permission(
        self,
        user_id: str,
        *,
        function_name: str,
        action_name: str,
    ) -> bool:
        """Kiểm tra vai trò của người dùng có một quyền chức năng/hành động."""

        manager_user = self._require_manager_user(user_id)
        if manager_user.user_status != ACTIVE_USER_STATUS:
            return False
        return self.permission_repository.role_has_permission(
            manager_user.role_id,
            function_name=self._required_text(function_name, "function_name"),
            action_name=self._required_text(action_name, "action_name"),
        )

    def _require_manager_user(self, user_id: str) -> ManagerUserModel:
        manager_user = self.manager_user_repository.get_by_id(user_id)
        if manager_user is None:
            raise ManagerUserNotFound("Manager user not found")
        return manager_user

    @staticmethod
    def _require_usable_session(
        user_session: UserSessionModel,
        now: datetime,
    ) -> None:
        if user_session.revoked_at is not None:
            raise UserSessionRevoked("User session has been revoked")
        if user_session.expires_at <= now:
            raise UserSessionExpired("User session has expired")

    @staticmethod
    def _constraint_name(exc: IntegrityError) -> str | None:
        diagnostic = getattr(exc.orig, "diag", None)
        return getattr(diagnostic, "constraint_name", None)

    def _translate_session_integrity_error(self, exc: IntegrityError) -> None:
        if self._constraint_name(exc) == "user_session_refresh_token_hash_key":
            raise RefreshTokenAlreadyExists(
                "Refresh-token hash already exists"
            ) from exc
        raise exc

    @staticmethod
    def _normalize_email(email: str) -> str:
        normalized_email = email.strip().lower()
        if not EMAIL_PATTERN.fullmatch(normalized_email):
            raise ValueError("email must be a valid email address")
        return normalized_email

    @staticmethod
    def _required_text(value: str, field_name: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(f"{field_name} must not be empty")
        return normalized_value


class ManagerUserService:
    """Các ca sử dụng quản trị người dùng và ranh giới giao dịch tương ứng."""

    def __init__(
        self,
        session: Session,
        manager_user_repository: ManagerUserRepository,
        role_repository: RoleRepository,
        user_session_repository: UserSessionRepository,
        password_hasher: Argon2PasswordHasher,
        *,
        clock: Callable[[], datetime] = utc_now,
        id_factory: Callable[[str, datetime], str] = generate_dated_identifier,
    ):
        self.session = session
        self.manager_user_repository = manager_user_repository
        self.role_repository = role_repository
        self.user_session_repository = user_session_repository
        self.password_hasher = password_hasher
        self.clock = clock
        self.id_factory = id_factory

    def get_manager_user(self, user_id: str) -> ManagerUserModel:
        """Lấy một người dùng quản trị hoặc báo lỗi nếu không tồn tại."""

        return self._require_manager_user(user_id)

    def list_manager_users(
        self, *, offset: int = 0, limit: int = 20
    ) -> list[ManagerUserModel]:
        """Liệt kê người dùng theo phân trang có giới hạn an toàn."""

        if offset < 0:
            raise ValueError("offset must be greater than or equal to 0")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return self.manager_user_repository.list(offset=offset, limit=limit)

    def create_manager_user(
        self,
        *,
        role_id: str,
        email: str,
        password: str,
        full_name: str,
        user_status: str | ManagerUserStatus = ACTIVE_USER_STATUS,
    ) -> ManagerUserModel:
        """Tạo người dùng mới sau khi kiểm tra email và vai trò."""

        normalized_email = self._normalize_email(email)
        normalized_name = self._required_text(full_name, "full_name")

        # Chỉ hash mới được gán vào model; plaintext không được lưu trong entity
        # hoặc truyền xuống repository.
        password_hash = self.password_hasher.hash_password(password)
        normalized_status = self._normalize_user_status(user_status)
        created_at = self.clock()

        try:
            with self.session.begin():
                self._require_available_email(normalized_email)
                self._require_role(role_id)
                manager_user = ManagerUserModel(
                    id=self.id_factory("user", created_at),
                    role_id=role_id,
                    email=normalized_email,
                    password_hash=password_hash,
                    full_name=normalized_name,
                    user_status=normalized_status,
                    created_at=created_at,
                    last_updated_at=created_at,
                    last_login_at=None,
                )
                self.manager_user_repository.add(manager_user)
                self.session.flush()
        except IntegrityError as exc:
            self._translate_manager_user_integrity_error(exc)

        return manager_user

    def update_manager_user(
        self,
        user_id: str,
        *,
        role_id: str | None = None,
        email: str | None = None,
        full_name: str | None = None,
        user_status: str | ManagerUserStatus | None = None,
    ) -> ManagerUserModel:
        """Cập nhật người dùng và thu hồi phiên khi tài khoản bị vô hiệu hóa."""

        now = self.clock()
        try:
            with self.session.begin():
                manager_user = self._require_manager_user(user_id)
                changed = False
                status_changed_to_inactive = False

                if role_id is not None and role_id != manager_user.role_id:
                    self._require_role(role_id)
                    manager_user.role_id = role_id
                    changed = True
                if email is not None:
                    normalized_email = self._normalize_email(email)
                    if normalized_email != manager_user.email:
                        self._require_available_email(normalized_email)
                        manager_user.email = normalized_email
                        changed = True
                if full_name is not None:
                    normalized_name = self._required_text(full_name, "full_name")
                    if normalized_name != manager_user.full_name:
                        manager_user.full_name = normalized_name
                        changed = True
                if user_status is not None:
                    normalized_status = self._normalize_user_status(user_status)
                    if normalized_status != manager_user.user_status:
                        manager_user.user_status = normalized_status
                        status_changed_to_inactive = (
                            normalized_status != ACTIVE_USER_STATUS
                        )
                        changed = True

                if changed:
                    manager_user.last_updated_at = now
                    if status_changed_to_inactive:
                        self.user_session_repository.revoke_all_active_for_user(
                            manager_user.id,
                            now,
                        )
                    self.session.flush()
        except IntegrityError as exc:
            self._translate_manager_user_integrity_error(exc)

        return manager_user

    def change_password(
        self,
        user_id: str,
        password: str,
    ) -> ManagerUserModel:
        """Băm mật khẩu mới và thu hồi toàn bộ phiên đang hoạt động."""

        password_hash = self.password_hasher.hash_password(password)
        now = self.clock()
        with self.session.begin():
            manager_user = self._require_manager_user(user_id)
            manager_user.password_hash = password_hash
            manager_user.last_updated_at = now
            self.user_session_repository.revoke_all_active_for_user(
                user_id,
                now,
            )
            self.session.flush()
        return manager_user

    def _require_role(self, role_id: str) -> None:
        if self.role_repository.get_by_id(role_id) is None:
            raise RoleNotFound("Role not found")

    def _require_available_email(self, email: str) -> None:
        if self.manager_user_repository.get_by_email(email) is not None:
            raise ManagerUserEmailAlreadyExists("Manager user email already exists")

    def _require_manager_user(self, user_id: str) -> ManagerUserModel:
        manager_user = self.manager_user_repository.get_by_id(user_id)
        if manager_user is None:
            raise ManagerUserNotFound("Manager user not found")
        return manager_user

    @staticmethod
    def _normalize_email(email: str) -> str:
        normalized_email = email.strip().lower()
        if not EMAIL_PATTERN.fullmatch(normalized_email):
            raise ValueError("email must be a valid email address")
        return normalized_email

    @staticmethod
    def _normalize_user_status(
        user_status: str | ManagerUserStatus,
    ) -> ManagerUserStatus:
        if isinstance(user_status, ManagerUserStatus):
            return user_status
        try:
            return ManagerUserStatus(user_status.strip().upper())
        except ValueError:
            raise ValueError("user_status must be 'ACTIVE' or 'INACTIVE'") from None

    @staticmethod
    def _required_text(value: str, field_name: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(f"{field_name} must not be empty")
        return normalized_value

    @staticmethod
    def _constraint_name(exc: IntegrityError) -> str | None:
        diagnostic = getattr(exc.orig, "diag", None)
        return getattr(diagnostic, "constraint_name", None)

    def _translate_manager_user_integrity_error(
        self,
        exc: IntegrityError,
    ) -> None:
        constraint_name = self._constraint_name(exc)
        if constraint_name == "manager_user_email_key":
            raise ManagerUserEmailAlreadyExists(
                "Manager user email already exists"
            ) from exc
        if constraint_name == "manager_user_role_id_fkey":
            raise RoleNotFound("Role not found") from exc
        raise exc


class RoleService:
    """Các ca sử dụng quản lý vai trò và tập quyền của vai trò."""

    def __init__(
        self,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        session: Session | None = None,
        role_permission_repository: RolePermissionRepository | None = None,
        *,
        clock: Callable[[], datetime] = utc_now,
        id_factory: Callable[[str], str] = generate_reference_identifier,
    ):
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.session = session
        self.role_permission_repository = role_permission_repository
        self.clock = clock
        self.id_factory = id_factory

    def get_role(self, role_id: str) -> RoleModel:
        """Lấy vai trò theo mã hoặc báo lỗi nếu không tồn tại."""

        role = self.role_repository.get_by_id(role_id)
        if role is None:
            raise RoleNotFound("Role not found")
        return role

    def list_roles(self) -> list[RoleModel]:
        """Liệt kê toàn bộ vai trò."""

        return self.role_repository.list_all()

    def list_role_permissions(self, role_id: str) -> list[PermissionModel]:
        """Liệt kê quyền của một vai trò đã tồn tại."""

        self.get_role(role_id)
        return self.permission_repository.list_by_role_id(role_id)

    def list_permissions(self) -> list[PermissionModel]:
        """Liệt kê permission catalog để giao diện cấu hình role sử dụng."""

        return self.permission_repository.list_all()

    def create_role(
        self,
        *,
        name: str,
        description: str | None,
        permission_ids: list[str],
        actor_user_id: str,
    ) -> RoleModel:
        """Tạo role và gán tập permission ban đầu trong cùng transaction."""

        session, role_permissions = self._write_collaborators()
        normalized_name = self._required_text(name, "name")
        normalized_description = self._optional_text(description)
        unique_permission_ids = list(dict.fromkeys(permission_ids))
        now = self.clock()
        try:
            with session.begin():
                if self.role_repository.get_by_name(normalized_name) is not None:
                    raise RoleNameAlreadyExists("Role name already exists")
                self._require_permissions(unique_permission_ids)
                role = RoleModel(
                    id=self.id_factory("role"),
                    name=normalized_name,
                    description=normalized_description,
                    created_by=actor_user_id,
                    last_updated_by=actor_user_id,
                    created_at=now,
                    last_updated_at=now,
                )
                self.role_repository.add(role)
                for permission_id in unique_permission_ids:
                    role_permissions.add(
                        RolePermissionModel(
                            role_id=role.id,
                            permission_id=permission_id,
                        )
                    )
                session.flush()
        except IntegrityError as exc:
            self._translate_role_integrity_error(exc)
        return role

    def update_role(
        self,
        role_id: str,
        *,
        actor_user_id: str,
        name: str | None = None,
        description: str | None = None,
        update_description: bool = False,
    ) -> RoleModel:
        """Cập nhật metadata role và người thực hiện thay đổi."""

        session, _role_permissions = self._write_collaborators()
        now = self.clock()
        try:
            with session.begin():
                role = self.get_role(role_id)
                changed = False
                if name is not None:
                    normalized_name = self._required_text(name, "name")
                    if normalized_name != role.name:
                        duplicate = self.role_repository.get_by_name(normalized_name)
                        if duplicate is not None:
                            raise RoleNameAlreadyExists("Role name already exists")
                        role.name = normalized_name
                        changed = True
                if update_description:
                    normalized_description = self._optional_text(description)
                    if normalized_description != role.description:
                        role.description = normalized_description
                        changed = True
                if changed:
                    role.last_updated_by = actor_user_id
                    role.last_updated_at = now
                    session.flush()
        except IntegrityError as exc:
            self._translate_role_integrity_error(exc)
        return role

    def replace_role_permissions(
        self,
        role_id: str,
        *,
        permission_ids: list[str],
        actor_user_id: str,
    ) -> list[PermissionModel]:
        """Thay toàn bộ tập quyền của role theo cách nguyên tử."""

        session, role_permissions = self._write_collaborators()
        now = self.clock()
        unique_permission_ids = list(dict.fromkeys(permission_ids))
        with session.begin():
            role = self.get_role(role_id)
            self._require_permissions(unique_permission_ids)
            existing = {
                item.permission_id
                for item in role_permissions.list_by_role_id(role_id)
            }
            requested = set(unique_permission_ids)
            for permission_id in existing - requested:
                role_permissions.remove(role_id, permission_id)
            for permission_id in requested - existing:
                role_permissions.add(
                    RolePermissionModel(
                        role_id=role_id,
                        permission_id=permission_id,
                    )
                )
            role.last_updated_by = actor_user_id
            role.last_updated_at = now
            session.flush()
            permissions = self.permission_repository.list_by_role_id(role_id)
        return permissions

    def _require_permissions(self, permission_ids: list[str]) -> None:
        for permission_id in permission_ids:
            if self.permission_repository.get_by_id(permission_id) is None:
                raise PermissionNotFound("Permission not found")

    def _write_collaborators(
        self,
    ) -> tuple[Session, RolePermissionRepository]:
        if self.session is None or self.role_permission_repository is None:
            raise RuntimeError("RoleService write collaborators are not configured")
        return self.session, self.role_permission_repository

    @staticmethod
    def _required_text(value: str, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must not be empty")
        return normalized

    @staticmethod
    def _optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _translate_role_integrity_error(exc: IntegrityError) -> None:
        diagnostic = getattr(exc.orig, "diag", None)
        constraint_name = getattr(diagnostic, "constraint_name", None)
        if constraint_name == "role_name_key":
            raise RoleNameAlreadyExists("Role name already exists") from exc
        if constraint_name == "role_permission_permission_id_fkey":
            raise PermissionNotFound("Permission not found") from exc
        raise exc
