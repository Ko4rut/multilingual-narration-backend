from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.identity.exceptions import (
    InactiveManagerUser,
    InvalidAccessToken,
    InvalidCredentials,
    ManagerUserNotFound,
    RefreshTokenAlreadyExists,
    UserSessionExpired,
    UserSessionNotFound,
    UserSessionRevoked,
)
from app.domains.identity.models.manager_user import (
    ManagerUserModel,
    ManagerUserStatus,
)
from app.domains.identity.models.user_session import UserSessionModel
from app.domains.identity.repositories.manager_user import ManagerUserRepository
from app.domains.identity.repositories.permission import PermissionRepository
from app.domains.identity.repositories.user_session import UserSessionRepository
from app.domains.identity.security import (
    AccessTokenClaims,
    Argon2PasswordHasher,
    IssuedAccessToken,
    JwtAccessTokenSigner,
    SecureRefreshTokenManager,
)
from app.domains.identity.utils.identity import (
    generate_dated_identifier,
    normalize_email,
    required_text,
    utc_now,
)


ACTIVE_USER_STATUS = ManagerUserStatus.ACTIVE


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


class AuthenticationService:
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

    def authenticate_and_issue_access_token(self, *, email: str, password: str) -> CredentialLoginResult:
        """Xác minh credential, tạo session rồi cấp cặp token."""

        # 1. Chuẩn hoá email và tìm user theo email đã chuẩn hoá. Nếu email sai định dạng, raise ngay ValidationError từ Pydantic (không cần try/except).
        normalized_email = normalize_email(email)
        manager_user = self.manager_user_repository.get_by_email(normalized_email)

        # 2. Verify password NGOÀI transaction.
        #    - Nếu user tồn tại: verify với password_hash thật.
        #    - Nếu user không tồn tại: truyền None → hasher dùng dummy hash để
        #      thời gian verify tương đương trường hợp có user → chống dò tài khoản
        #      (timing attack).
        #    - Đặt ngoài transaction để login sai không tốn transaction/connection.
        is_valid_password = self.password_hasher.verify_password(
            password,
            manager_user.password_hash if manager_user is not None else None,
        )

        # 4. Gộp điều kiện "không tìm thấy user" và "sai password" thành cùng một
        #    exception InvalidCredentials → client không phân biệt được email sai
        #    hay password sai → tránh enumeration.
        if manager_user is None or not is_valid_password:
            raise InvalidCredentials("Invalid email or password")

        # 5. Kiểm tra trạng thái tài khoản. Chỉ user ACTIVE mới được đăng nhập.
        #    Tách riêng exception InactiveManagerUser để client biết lý do cụ thể
        #    (khác với sai credential).
        if manager_user.user_status != ACTIVE_USER_STATUS:
            raise InactiveManagerUser("Manager user is inactive")

        # 6. Lấy thời điểm hiện tại từ clock (inject được để test).
        #    Dùng cùng một created_at cho session, last_login_at và expires_at
        #    để đảm bảo tính nhất quán trong một lần đăng nhập.
        created_at = self.clock()

        # 7. Mở transaction CHỈ cho phần ghi dữ liệu (tạo session, cập nhật
        #    last_login_at). Verify đã xong ở trên nên transaction không bị mở
        #    cho các lần login sai.
        try:
            with self.session.begin():

                # 8. Sinh refresh token ngẫu nhiên (plaintext trả về client qua cookie).
                #    Đối tượng issued_refresh_token chứa cả token thô và token_hash.
                issued_refresh_token = self.refresh_token_manager.issue_refresh_token()

                # 9. Tạo UserSessionModel:
                #    - id: sinh từ id_factory (prefix "sess" + timestamp).
                #    - user_id: liên kết với user vừa xác thực.
                #    - refresh_token_hash: CHỈ lưu hash (SHA-256), không lưu token thô.
                #    - expires_at: created_at + TTL của refresh token.
                #    - revoked_at = None: session mới, chưa bị thu hồi.
                user_session = UserSessionModel(
                    id=self.id_factory("sess", created_at),
                    user_id=manager_user.id,
                    refresh_token_hash=issued_refresh_token.token_hash,
                    expires_at=created_at + self.refresh_token_ttl,
                    created_at=created_at,
                    revoked_at=None,
                )

                # 10. Cập nhật last_login_at trên user.
                #     Vì manager_user là persistent (lấy từ repository trong cùng
                #     session), gán thuộc tính là đủ — dirty tracking sẽ sinh UPDATE
                #     khi commit. Không cần gọi repo.update().
                manager_user.last_login_at = created_at

                # 11. Đưa session mới vào persistence layer.
                #     user_session là transient → phải add() để session biết
                #     → commit sẽ sinh INSERT.
                self.user_session_repository.add(user_session)

                # 12. Flush để SQLAlchemy gửi INSERT xuống DB NGAY (chưa commit).
                #     Mục đích: phát hiện sớm lỗi ràng buộc (unique, FK) TRƯỚC khi
                #     ký access token, và đảm bảo user_session có id ổn định.
                self.session.flush()

                # 13. Ký access token JWT với:
                #     - sub: user id
                #     - sid: session id (vừa có sau flush)
                #     - role_id: để RBAC kiểm tra nhanh mà không cần query DB
                #     Access token KHÔNG được lưu DB — chỉ ký và trả về client.
                access_token = self.access_token_signer.issue_access_token(
                    user_id=manager_user.id,
                    session_id=user_session.id,
                    role_id=manager_user.role_id,
                )

        # 14. Bắt IntegrityError (vi phạm unique/FK) — ví dụ race condition khi
        #     hai request cùng tạo session trùng id, hoặc user bị xoá giữa chừng.
        #     Chuyển thành exception nghiệp vụ phù hợp thay vì để lộ lỗi DB (500).
        except IntegrityError as exc:
            self._translate_session_integrity_error(exc)

        # 15. Trả về kết quả cho tầng HTTP:
        return CredentialLoginResult(
            manager_user=manager_user,                  # manager_user: để router lấy thông tin (email, full_name, ...)
            user_session=user_session,                  # user_session: để router biết expires_at (tính expires_in)
            access_token=access_token,                  # access_token: trả trong body response
            refresh_token=issued_refresh_token.token,   # refresh_token: token THÔ, router sẽ set vào cookie HttpOnly
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
            function_name=required_text(function_name, "function_name"),
            action_name=required_text(action_name, "action_name"),
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

