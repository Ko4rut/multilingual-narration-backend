from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.identity.enums import ManagerUserStatus
from app.domains.identity.exceptions import (
    InactiveManagerUser,
    InvalidCredentials,
    ManagerUserEmailAlreadyExists,
    ManagerUserNotFound,
    RefreshTokenAlreadyExists,
    RoleNotFound,
    UserSessionExpired,
    UserSessionNotFound,
    UserSessionRevoked,
)
from app.domains.identity.models.manager_user import ManagerUserModel
from app.domains.identity.models.permission import PermissionModel
from app.domains.identity.models.role import RoleModel
from app.domains.identity.models.user_session import UserSessionModel
from app.domains.identity.repositories.manager_user import ManagerUserRepository
from app.domains.identity.repositories.permission import PermissionRepository
from app.domains.identity.repositories.role import RoleRepository
from app.domains.identity.repositories.user_session import UserSessionRepository
from app.domains.identity.security.jwt import (
    AccessTokenClaims,
    AccessTokenProvider,
    IssuedAccessToken,
)
from app.domains.identity.security.password import PasswordProvider
from app.domains.identity.utils.identity import generate_dated_identifier, utc_now


ACTIVE_USER_STATUS = ManagerUserStatus.ACTIVE
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class LoginResult:
    manager_user: ManagerUserModel
    user_session: UserSessionModel
    access_token: IssuedAccessToken


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    manager_user: ManagerUserModel
    user_session: UserSessionModel
    claims: AccessTokenClaims


class IdentityService:
    """Authentication, session lifecycle, and RBAC checks."""

    def __init__(
        self,
        session: Session,
        manager_user_repository: ManagerUserRepository,
        user_session_repository: UserSessionRepository,
        permission_repository: PermissionRepository,
        password_provider: PasswordProvider,
        access_token_provider: AccessTokenProvider,
        *,
        clock: Callable[[], datetime] = utc_now,
        id_factory: Callable[[str, datetime], str] = generate_dated_identifier,
    ):
        self.session = session
        self.manager_user_repository = manager_user_repository
        self.user_session_repository = user_session_repository
        self.permission_repository = permission_repository
        self.password_provider = password_provider
        self.access_token_provider = access_token_provider
        self.clock = clock
        self.id_factory = id_factory

    def login(
        self,
        *,
        email: str,
        password: str,
        refresh_token_hash: str,
        expires_at: datetime,
    ) -> LoginResult:
        normalized_email = self._normalize_email(email)
        token_hash = self._normalize_sha256_hash(refresh_token_hash)
        created_at = self.clock()
        self._require_timezone_aware(expires_at, "expires_at")
        if expires_at <= created_at:
            raise ValueError("expires_at must be later than the current time")

        try:
            with self.session.begin():
                manager_user = self.manager_user_repository.get_by_email(
                    normalized_email
                )
                password_verification = self.password_provider.verify_password(
                    password,
                    manager_user.password_hash if manager_user is not None else None,
                )
                if manager_user is None or not password_verification.is_valid:
                    raise InvalidCredentials("Invalid email or password")
                self._require_active_manager_user(manager_user)
                if password_verification.updated_hash is not None:
                    manager_user.password_hash = password_verification.updated_hash
                if (
                    self.user_session_repository.get_by_refresh_token_hash(token_hash)
                    is not None
                ):
                    raise RefreshTokenAlreadyExists("Refresh-token hash already exists")

                user_session = UserSessionModel(
                    id=self.id_factory("sess", created_at),
                    user_id=manager_user.id,
                    refresh_token_hash=token_hash,
                    expires_at=expires_at,
                    created_at=created_at,
                    revoked_at=None,
                )
                manager_user.last_login_at = created_at
                self.user_session_repository.add(user_session)
                self.session.flush()
                access_token = self.access_token_provider.issue_access_token(
                    user_id=manager_user.id,
                    session_id=user_session.id,
                    role_id=manager_user.role_id,
                )
        except IntegrityError as exc:
            self._translate_session_integrity_error(exc)

        return LoginResult(
            manager_user=manager_user,
            user_session=user_session,
            access_token=access_token,
        )

    def authenticate_access_token(self, token: str) -> AuthenticatedIdentity:
        claims = self.access_token_provider.decode_access_token(token)
        user_session = self.user_session_repository.get_by_id(claims.session_id)
        if user_session is None or user_session.user_id != claims.user_id:
            raise UserSessionNotFound("User session not found")
        self._require_usable_session(user_session, self.clock())
        manager_user = self._require_manager_user(claims.user_id)
        self._require_active_manager_user(manager_user)
        return AuthenticatedIdentity(
            manager_user=manager_user,
            user_session=user_session,
            claims=claims,
        )

    def refresh(self, refresh_token_hash: str) -> UserSessionModel:
        token_hash = self._normalize_sha256_hash(refresh_token_hash)
        user_session = self.user_session_repository.get_by_refresh_token_hash(
            token_hash
        )
        if user_session is None:
            raise UserSessionNotFound("User session not found")
        self._require_usable_session(user_session, self.clock())
        manager_user = self._require_manager_user(user_session.user_id)
        self._require_active_manager_user(manager_user)
        return user_session

    def logout(self, refresh_token_hash: str) -> UserSessionModel:
        token_hash = self._normalize_sha256_hash(refresh_token_hash)
        revoked_at = self.clock()
        with self.session.begin():
            user_session = self.user_session_repository.get_by_refresh_token_hash(
                token_hash
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
        manager_user = self._require_manager_user(user_id)
        if manager_user.user_status != ACTIVE_USER_STATUS:
            return False
        return self.permission_repository.role_has_permission(
            manager_user.role_id,
            function_name=self._required_text(function_name, "function_name"),
            action_name=self._required_text(action_name, "action_name"),
        )

    @staticmethod
    def _require_usable_session(
        user_session: UserSessionModel,
        now: datetime,
    ) -> None:
        if user_session.revoked_at is not None:
            raise UserSessionRevoked("User session has been revoked")
        if user_session.expires_at <= now:
            raise UserSessionExpired("User session has expired")

    def _require_manager_user(self, user_id: str) -> ManagerUserModel:
        manager_user = self.manager_user_repository.get_by_id(user_id)
        if manager_user is None:
            raise ManagerUserNotFound("Manager user not found")
        return manager_user

    @staticmethod
    def _require_active_manager_user(manager_user: ManagerUserModel) -> None:
        if manager_user.user_status != ACTIVE_USER_STATUS:
            raise InactiveManagerUser("Manager user is inactive")

    @staticmethod
    def _normalize_email(email: str) -> str:
        normalized_email = email.strip().lower()
        if not EMAIL_PATTERN.fullmatch(normalized_email):
            raise ValueError("email must be a valid email address")
        return normalized_email

    @staticmethod
    def _normalize_sha256_hash(value: str) -> str:
        normalized_value = value.strip().lower()
        if not SHA256_PATTERN.fullmatch(normalized_value):
            raise ValueError("refresh_token_hash must be a SHA-256 hexadecimal digest")
        return normalized_value

    @staticmethod
    def _require_timezone_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must include timezone information")

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

    def _translate_session_integrity_error(self, exc: IntegrityError) -> None:
        if self._constraint_name(exc) == "user_session_refresh_token_hash_key":
            raise RefreshTokenAlreadyExists(
                "Refresh-token hash already exists"
            ) from exc
        raise exc


class ManagerUserService:
    """Administrative manager-user use cases and transaction boundaries."""

    def __init__(
        self,
        session: Session,
        manager_user_repository: ManagerUserRepository,
        role_repository: RoleRepository,
        user_session_repository: UserSessionRepository,
        password_provider: PasswordProvider,
        *,
        clock: Callable[[], datetime] = utc_now,
        id_factory: Callable[[str, datetime], str] = generate_dated_identifier,
    ):
        self.session = session
        self.manager_user_repository = manager_user_repository
        self.role_repository = role_repository
        self.user_session_repository = user_session_repository
        self.password_provider = password_provider
        self.clock = clock
        self.id_factory = id_factory

    def get_manager_user(self, user_id: str) -> ManagerUserModel:
        return self._require_manager_user(user_id)

    def list_manager_users(
        self, *, offset: int = 0, limit: int = 20
    ) -> list[ManagerUserModel]:
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
        normalized_email = self._normalize_email(email)
        normalized_name = self._required_text(full_name, "full_name")
        password_hash = self.password_provider.hash_password(password)
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
        password_hash = self.password_provider.hash_password(password)
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
    """Role and role-permission read use cases."""

    def __init__(
        self,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
    ):
        self.role_repository = role_repository
        self.permission_repository = permission_repository

    def get_role(self, role_id: str) -> RoleModel:
        role = self.role_repository.get_by_id(role_id)
        if role is None:
            raise RoleNotFound("Role not found")
        return role

    def list_roles(self) -> list[RoleModel]:
        return self.role_repository.list_all()

    def list_role_permissions(self, role_id: str) -> list[PermissionModel]:
        self.get_role(role_id)
        return self.permission_repository.list_by_role_id(role_id)
