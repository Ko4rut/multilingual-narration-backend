from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.domains.identity.enums import ManagerUserStatus
from app.domains.identity.exceptions import (
    InactiveManagerUser,
    InvalidCredentials,
    ManagerUserEmailAlreadyExists,
    ManagerUserNotFound,
    RoleNotFound,
    UserSessionExpired,
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
from app.domains.identity.services.identity import (
    IdentityService,
    ManagerUserService,
    RoleService,
)


NOW = datetime(2026, 10, 26, 8, 30, tzinfo=timezone.utc)
USER_ID = "user-261026-12345678"
SESSION_ID = "sess-261026-12345678"
TOKEN_HASH = "a" * 64


def build_user(
    *, status: ManagerUserStatus = ManagerUserStatus.ACTIVE
) -> ManagerUserModel:
    return ManagerUserModel(
        id=USER_ID,
        role_id="role-12345678",
        email="admin@mnr.local",
        password_hash="secure-password-hash",
        full_name="Administrator",
        user_status=status,
        created_at=NOW,
        last_updated_at=NOW,
        last_login_at=None,
    )


def build_session(
    *,
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> UserSessionModel:
    return UserSessionModel(
        id=SESSION_ID,
        user_id=USER_ID,
        refresh_token_hash=TOKEN_HASH,
        expires_at=expires_at or NOW + timedelta(days=1),
        created_at=NOW,
        revoked_at=revoked_at,
    )


def build_identity_service():
    session = MagicMock(spec=Session)
    user_repository = MagicMock(spec=ManagerUserRepository)
    user_session_repository = MagicMock(spec=UserSessionRepository)
    permission_repository = MagicMock(spec=PermissionRepository)
    service = IdentityService(
        session,
        user_repository,
        user_session_repository,
        permission_repository,
        lambda password, password_hash: (
            password == "correct-password" and password_hash == "secure-password-hash"
        ),
        clock=lambda: NOW,
        id_factory=lambda _prefix, _created_at: SESSION_ID,
    )
    return (
        service,
        session,
        user_repository,
        user_session_repository,
        permission_repository,
    )


def build_manager_user_service():
    session = MagicMock(spec=Session)
    user_repository = MagicMock(spec=ManagerUserRepository)
    role_repository = MagicMock(spec=RoleRepository)
    user_session_repository = MagicMock(spec=UserSessionRepository)
    service = ManagerUserService(
        session,
        user_repository,
        role_repository,
        user_session_repository,
        clock=lambda: NOW,
        id_factory=lambda _prefix, _created_at: USER_ID,
    )
    return (
        service,
        session,
        user_repository,
        role_repository,
        user_session_repository,
    )


def test_login_creates_session_and_records_last_login():
    service, session, users, user_sessions, _permissions = build_identity_service()
    manager_user = build_user()
    users.get_by_email.return_value = manager_user
    user_sessions.get_by_refresh_token_hash.return_value = None

    result = service.login(
        email=" ADMIN@MNR.LOCAL ",
        password="correct-password",
        refresh_token_hash=TOKEN_HASH,
        expires_at=NOW + timedelta(days=1),
    )

    assert result.manager_user is manager_user
    assert result.user_session.id == SESSION_ID
    assert result.user_session.user_id == USER_ID
    assert manager_user.last_login_at == NOW
    user_sessions.add.assert_called_once_with(result.user_session)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("user", "password", "error"),
    [
        (None, "correct-password", InvalidCredentials),
        (build_user(), "wrong-password", InvalidCredentials),
        (
            build_user(status=ManagerUserStatus.INACTIVE),
            "correct-password",
            InactiveManagerUser,
        ),
    ],
)
def test_login_rejects_invalid_or_inactive_user(user, password, error):
    service, _session, users, _user_sessions, _permissions = build_identity_service()
    users.get_by_email.return_value = user

    with pytest.raises(error):
        service.login(
            email="admin@mnr.local",
            password=password,
            refresh_token_hash=TOKEN_HASH,
            expires_at=NOW + timedelta(days=1),
        )


@pytest.mark.parametrize(
    ("user_session", "error"),
    [
        (build_session(expires_at=NOW), UserSessionExpired),
        (build_session(revoked_at=NOW), UserSessionRevoked),
    ],
)
def test_refresh_rejects_unusable_session(user_session, error):
    service, _session, _users, user_sessions, _permissions = build_identity_service()
    user_sessions.get_by_refresh_token_hash.return_value = user_session

    with pytest.raises(error):
        service.refresh(TOKEN_HASH)


def test_logout_revokes_only_the_selected_session():
    service, session, _users, user_sessions, _permissions = build_identity_service()
    user_session = build_session()
    user_sessions.get_by_refresh_token_hash.return_value = user_session

    result = service.logout(TOKEN_HASH)

    assert result is user_session
    assert result.revoked_at == NOW
    session.flush.assert_called_once_with()


def test_has_permission_requires_active_user():
    service, _session, users, _user_sessions, permissions = build_identity_service()
    users.get_by_id.return_value = build_user()
    permissions.role_has_permission.return_value = True

    assert service.has_permission(
        USER_ID,
        function_name="User Management",
        action_name="read",
    )

    permissions.role_has_permission.assert_called_once_with(
        "role-12345678",
        function_name="User Management",
        action_name="read",
    )


def test_create_manager_user_validates_role_and_normalizes_values():
    service, session, users, roles, _user_sessions = build_manager_user_service()
    users.get_by_email.return_value = None
    roles.get_by_id.return_value = MagicMock(spec=RoleModel)

    result = service.create_manager_user(
        role_id="role-12345678",
        email="  ADMIN@MNR.LOCAL ",
        password_hash=" secure-password-hash ",
        full_name=" Administrator ",
        user_status=" ACTIVE ",
    )

    assert result.id == USER_ID
    assert result.email == "admin@mnr.local"
    assert result.user_status is ManagerUserStatus.ACTIVE
    assert result.created_at == NOW
    users.add.assert_called_once_with(result)
    session.flush.assert_called_once_with()


def test_create_manager_user_rejects_duplicate_email_and_unknown_role():
    service, _session, users, roles, _user_sessions = build_manager_user_service()
    users.get_by_email.return_value = build_user()
    with pytest.raises(ManagerUserEmailAlreadyExists):
        service.create_manager_user(
            role_id="role-12345678",
            email="admin@mnr.local",
            password_hash="secure-password-hash",
            full_name="Administrator",
        )

    users.get_by_email.return_value = None
    roles.get_by_id.return_value = None
    with pytest.raises(RoleNotFound):
        service.create_manager_user(
            role_id="role-missing",
            email="other@mnr.local",
            password_hash="secure-password-hash",
            full_name="Other User",
        )


def test_deactivating_user_revokes_active_sessions():
    service, session, users, _roles, user_sessions = build_manager_user_service()
    manager_user = build_user()
    users.get_by_id.return_value = manager_user

    result = service.update_manager_user(USER_ID, user_status="inactive")

    assert result.user_status is ManagerUserStatus.INACTIVE
    assert result.last_updated_at == NOW
    user_sessions.revoke_all_active_for_user.assert_called_once_with(USER_ID, NOW)
    session.flush.assert_called_once_with()


def test_change_password_revokes_active_sessions():
    service, session, users, _roles, user_sessions = build_manager_user_service()
    manager_user = build_user()
    users.get_by_id.return_value = manager_user

    result = service.change_password_hash(USER_ID, "new-secure-hash")

    assert result.password_hash == "new-secure-hash"
    user_sessions.revoke_all_active_for_user.assert_called_once_with(USER_ID, NOW)
    session.flush.assert_called_once_with()


def test_get_manager_user_raises_domain_error_when_missing():
    service, _session, users, _roles, _user_sessions = build_manager_user_service()
    users.get_by_id.return_value = None

    with pytest.raises(ManagerUserNotFound):
        service.get_manager_user("user-missing")


@pytest.mark.parametrize(
    ("offset", "limit"),
    [(-1, 20), (0, 0), (0, 101)],
)
def test_list_manager_users_rejects_invalid_pagination(offset, limit):
    service, _session, users, _roles, _user_sessions = build_manager_user_service()

    with pytest.raises(ValueError):
        service.list_manager_users(offset=offset, limit=limit)

    users.list.assert_not_called()


def test_role_service_gets_role_and_permissions():
    roles = MagicMock(spec=RoleRepository)
    permissions = MagicMock(spec=PermissionRepository)
    expected_role = MagicMock(spec=RoleModel)
    expected_permissions = [MagicMock(spec=PermissionModel)]
    roles.get_by_id.return_value = expected_role
    permissions.list_by_role_id.return_value = expected_permissions
    service = RoleService(roles, permissions)

    assert service.get_role("role-12345678") is expected_role
    assert service.list_role_permissions("role-12345678") == expected_permissions


def test_role_service_raises_domain_error_when_missing():
    roles = MagicMock(spec=RoleRepository)
    permissions = MagicMock(spec=PermissionRepository)
    roles.get_by_id.return_value = None
    service = RoleService(roles, permissions)

    with pytest.raises(RoleNotFound):
        service.get_role("role-missing")
