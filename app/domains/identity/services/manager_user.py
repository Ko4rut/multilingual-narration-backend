from collections.abc import Callable
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.identity.exceptions import (
    ManagerUserEmailAlreadyExists,
    ManagerUserNotFound,
    RoleNotFound,
)
from app.domains.identity.models.manager_user import (
    ManagerUserModel,
    ManagerUserStatus,
)
from app.domains.identity.repositories.manager_user import ManagerUserRepository
from app.domains.identity.repositories.role import RoleRepository
from app.domains.identity.repositories.user_session import UserSessionRepository
from app.domains.identity.security import Argon2PasswordHasher
from app.domains.identity.utils.identity import (
    generate_dated_identifier,
    normalize_email,
    required_text,
    utc_now,
)


ACTIVE_USER_STATUS = ManagerUserStatus.ACTIVE


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
        return self.manager_user_repository.get_all(offset=offset, limit=limit)

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

        normalized_email = normalize_email(email)
        normalized_name = required_text(full_name, "full_name")

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
        password: str | None = None,
    ) -> ManagerUserModel:
        """Cập nhật người dùng, băm mật khẩu mới và thu hồi phiên khi cần."""

        now = self.clock()
        try:
            with self.session.begin():
                manager_user = self._require_manager_user(user_id)
                changed = False
                must_revoke_sessions = False

                if role_id is not None and role_id != manager_user.role_id:
                    self._require_role(role_id)
                    manager_user.role_id = role_id
                    changed = True
                if email is not None:
                    normalized_email = normalize_email(email)
                    if normalized_email != manager_user.email:
                        self._require_available_email(normalized_email)
                        manager_user.email = normalized_email
                        changed = True
                if full_name is not None:
                    normalized_name = required_text(full_name, "full_name")
                    if normalized_name != manager_user.full_name:
                        manager_user.full_name = normalized_name
                        changed = True
                if user_status is not None:
                    normalized_status = self._normalize_user_status(user_status)
                    if normalized_status != manager_user.user_status:
                        manager_user.user_status = normalized_status
                        must_revoke_sessions = (
                            normalized_status != ACTIVE_USER_STATUS
                        )
                        changed = True
                if password is not None:
                    # PATCH nhận plaintext ở HTTP boundary nhưng entity chỉ giữ
                    # Argon2 hash. Đổi mật khẩu luôn vô hiệu hóa các phiên cũ.
                    manager_user.password_hash = (
                        self.password_hasher.hash_password(password)
                    )
                    must_revoke_sessions = True
                    changed = True

                if changed:
                    manager_user.last_updated_at = now
                    if must_revoke_sessions:
                        self.user_session_repository.revoke_all_active_for_user(
                            manager_user.id,
                            now,
                        )
                    self.session.flush()
        except IntegrityError as exc:
            self._translate_manager_user_integrity_error(exc)

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
