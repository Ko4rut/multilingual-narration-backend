from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.domains.identity.exceptions import (
    InactiveManagerUser,
    InvalidAccessToken,
    InvalidCredentials,
    ManagerUserEmailAlreadyExists,
    ManagerUserNotFound,
    RoleNotFound,
    RoleNameAlreadyExists,
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
from app.domains.identity.models.role_permission import RolePermissionModel
from app.domains.identity.models.user_session import UserSessionModel
from app.domains.identity.repositories.manager_user import ManagerUserRepository
from app.domains.identity.repositories.permission import PermissionRepository
from app.domains.identity.repositories.role import RoleRepository
from app.domains.identity.repositories.role_permission import RolePermissionRepository
from app.domains.identity.repositories.user_session import UserSessionRepository
from app.domains.identity.security import (
    AccessTokenClaims,
    Argon2PasswordHasher,
    IssuedAccessToken,
    IssuedRefreshToken,
    JwtAccessTokenSigner,
    SecureRefreshTokenManager,
)
from app.domains.identity.services.authentication import AuthenticationService
from app.domains.identity.services.manager_user import ManagerUserService
from app.domains.identity.services.role import RoleService


NOW = datetime(2026, 10, 26, 8, 30, tzinfo=timezone.utc)
USER_ID = "user-261026-12345678"
SESSION_ID = "sess-261026-12345678"
TOKEN_HASH = "a" * 64
ROTATED_TOKEN_HASH = "b" * 64


def build_user(
    *, status: ManagerUserStatus = ManagerUserStatus.ACTIVE
) -> ManagerUserModel:
    return ManagerUserModel(
        id=USER_ID,
        role_id="role-12345678",
        email="admin@mnr.local",
        password_hash="externally-generated-password-hash",
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
    password_hasher = MagicMock(spec=Argon2PasswordHasher)
    password_hasher.verify_password.side_effect = (
        lambda password, password_hash: password == "correct-password"
        and password_hash == "externally-generated-password-hash"
    )
    access_token_signer = MagicMock(spec=JwtAccessTokenSigner)
    access_token_signer.issue_access_token.return_value = IssuedAccessToken(
        token="signed-access-token",
        expires_at=NOW + timedelta(minutes=15),
    )
    refresh_token_manager = MagicMock(spec=SecureRefreshTokenManager)
    refresh_token_manager.hash_refresh_token.return_value = TOKEN_HASH
    refresh_token_manager.issue_refresh_token.return_value = IssuedRefreshToken(
        token="rotated-refresh-token",
        token_hash=ROTATED_TOKEN_HASH,
    )
    service = AuthenticationService(
        session=session,
        manager_user_repository=user_repository,
        user_session_repository=user_session_repository,
        permission_repository=permission_repository,
        password_hasher=password_hasher,
        access_token_signer=access_token_signer,
        refresh_token_manager=refresh_token_manager,
        clock=lambda: NOW,
        id_factory=lambda _prefix, _created_at: SESSION_ID,
    )
    return (
        service,
        user_repository,
        permission_repository,
        password_hasher,
        access_token_signer,
    )


def build_manager_user_service():
    session = MagicMock(spec=Session)
    user_repository = MagicMock(spec=ManagerUserRepository)
    role_repository = MagicMock(spec=RoleRepository)
    user_session_repository = MagicMock(spec=UserSessionRepository)
    password_hasher = MagicMock(spec=Argon2PasswordHasher)
    password_hasher.hash_password.side_effect = (
        lambda password: f"hashed:{password}"
    )
    service = ManagerUserService(
        session,
        user_repository,
        role_repository,
        user_session_repository,
        password_hasher,
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


def build_role_service():
    session = MagicMock(spec=Session)
    roles = MagicMock(spec=RoleRepository)
    permissions = MagicMock(spec=PermissionRepository)
    role_permissions = MagicMock(spec=RolePermissionRepository)
    service = RoleService(
        roles,
        permissions,
        session=session,
        role_permission_repository=role_permissions,
        clock=lambda: NOW,
        id_factory=lambda _prefix, _created_at: "role-12345678",
    )
    return service, session, roles, permissions, role_permissions


def test_has_permission_requires_active_user():
    service, users, permissions, _password_hasher, _signer = build_identity_service()
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


def test_inactive_user_has_no_permission():
    service, users, permissions, _password_hasher, _signer = build_identity_service()
    users.get_by_id.return_value = build_user(status=ManagerUserStatus.INACTIVE)

    assert not service.has_permission(
        USER_ID,
        function_name="User Management",
        action_name="read",
    )
    permissions.role_has_permission.assert_not_called()


def test_authenticate_credentials_verifies_stored_password_hash():
    service, users, _permissions, password_hasher, _signer = build_identity_service()
    manager_user = build_user()
    users.get_by_email.return_value = manager_user

    result = service.authenticate_credentials(
        email=" ADMIN@MNR.LOCAL ",
        password="correct-password",
    )

    assert result is manager_user
    users.get_by_email.assert_called_once_with("admin@mnr.local")
    password_hasher.verify_password.assert_called_once_with(
        "correct-password",
        manager_user.password_hash,
    )


@pytest.mark.parametrize(
    ("manager_user", "password", "expected_error"),
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
def test_authenticate_credentials_rejects_invalid_login(
    manager_user,
    password,
    expected_error,
):
    service, users, _permissions, password_hasher, _signer = build_identity_service()
    users.get_by_email.return_value = manager_user

    with pytest.raises(expected_error):
        service.authenticate_credentials(
            email="admin@mnr.local",
            password=password,
        )

    password_hasher.verify_password.assert_called_once_with(
        password,
        manager_user.password_hash if manager_user is not None else None,
    )


def test_login_signs_for_valid_user():
    service, users, _permissions, _password_hasher, signer = (
        build_identity_service()
    )
    manager_user = build_user()
    users.get_by_email.return_value = manager_user

    result = service.login(
        email="admin@mnr.local",
        password="correct-password",
    )

    assert result.manager_user is manager_user
    assert result.user_session.id == SESSION_ID
    assert result.user_session.refresh_token_hash == ROTATED_TOKEN_HASH
    assert result.refresh_token == "rotated-refresh-token"
    assert manager_user.last_login_at == NOW
    service.user_session_repository.add.assert_called_once_with(result.user_session)
    assert result.access_token.token == "signed-access-token"
    signer.issue_access_token.assert_called_once_with(
        user_id=USER_ID,
        session_id=SESSION_ID,
        role_id="role-12345678",
    )


def test_authenticate_access_token_checks_current_user_and_role():
    service, users, _permissions, _password_hasher, signer = (
        build_identity_service()
    )
    manager_user = build_user()
    claims = AccessTokenClaims(
        user_id=USER_ID,
        session_id=SESSION_ID,
        role_id="role-12345678",
        token_id="token-id-12345678",
        issued_at=NOW,
        not_before=NOW,
        expires_at=NOW + timedelta(minutes=15),
    )
    signer.decode_access_token.return_value = claims
    user_session = build_session()
    service.user_session_repository.get_by_id.return_value = user_session
    users.get_by_id.return_value = manager_user

    identity = service.authenticate_access_token("signed-access-token")

    assert identity.manager_user is manager_user
    assert identity.user_session is user_session
    assert identity.claims is claims
    signer.decode_access_token.assert_called_once_with("signed-access-token")


def test_authenticate_access_token_rejects_stale_role():
    service, users, _permissions, _password_hasher, signer = (
        build_identity_service()
    )
    claims = AccessTokenClaims(
        user_id=USER_ID,
        session_id=SESSION_ID,
        role_id="role-old-role",
        token_id="token-id-12345678",
        issued_at=NOW,
        not_before=NOW,
        expires_at=NOW + timedelta(minutes=15),
    )
    signer.decode_access_token.return_value = claims
    service.user_session_repository.get_by_id.return_value = build_session()
    users.get_by_id.return_value = build_user()

    with pytest.raises(InvalidAccessToken):
        service.authenticate_access_token("signed-access-token")


@pytest.mark.parametrize(
    ("user_session", "expected_error"),
    [
        (None, UserSessionNotFound),
        (build_session(expires_at=NOW), UserSessionExpired),
        (build_session(revoked_at=NOW), UserSessionRevoked),
    ],
)
def test_authenticate_access_token_rejects_unusable_session(
    user_session,
    expected_error,
):
    service, _users, _permissions, _password_hasher, signer = (
        build_identity_service()
    )
    signer.decode_access_token.return_value = AccessTokenClaims(
        user_id=USER_ID,
        session_id=SESSION_ID,
        role_id="role-12345678",
        token_id="token-id-12345678",
        issued_at=NOW,
        not_before=NOW,
        expires_at=NOW + timedelta(minutes=15),
    )
    service.user_session_repository.get_by_id.return_value = user_session

    with pytest.raises(expected_error):
        service.authenticate_access_token("signed-access-token")


@pytest.mark.parametrize(
    ("user_session", "expected_error"),
    [
        (build_session(expires_at=NOW), UserSessionExpired),
        (build_session(revoked_at=NOW), UserSessionRevoked),
    ],
)
def test_refresh_rejects_expired_or_revoked_session(
    user_session,
    expected_error,
):
    service, _users, _permissions, _password_hasher, _signer = (
        build_identity_service()
    )
    service.user_session_repository.get_by_refresh_token_hash_for_update.return_value = (
        user_session
    )

    with pytest.raises(expected_error):
        service.refresh("current-refresh-token")


def test_refresh_rotates_token_and_issues_new_access_token():
    service, users, _permissions, _password_hasher, signer = (
        build_identity_service()
    )
    user_session = build_session()
    manager_user = build_user()
    service.user_session_repository.get_by_refresh_token_hash_for_update.return_value = (
        user_session
    )
    users.get_by_id.return_value = manager_user

    result = service.refresh("current-refresh-token")

    assert result.user_session is user_session
    assert result.refresh_token == "rotated-refresh-token"
    assert user_session.refresh_token_hash == ROTATED_TOKEN_HASH
    signer.issue_access_token.assert_called_once_with(
        user_id=USER_ID,
        session_id=SESSION_ID,
        role_id="role-12345678",
    )


def test_rotated_refresh_token_cannot_be_reused():
    service, _users, _permissions, _password_hasher, signer = (
        build_identity_service()
    )
    service.user_session_repository.get_by_refresh_token_hash_for_update.return_value = (
        None
    )

    with pytest.raises(UserSessionNotFound):
        service.refresh("old-refresh-token")

    signer.issue_access_token.assert_not_called()


def test_logout_revokes_selected_session():
    service, _users, _permissions, _password_hasher, _signer = (
        build_identity_service()
    )
    user_session = build_session()
    service.user_session_repository.get_by_refresh_token_hash_for_update.return_value = (
        user_session
    )

    assert service.logout("current-refresh-token") is user_session
    assert user_session.revoked_at == NOW
    service.session.flush.assert_called_once_with()


def test_create_manager_user_validates_role_and_normalizes_values():
    service, session, users, roles, _user_sessions = build_manager_user_service()
    users.get_by_email.return_value = None
    roles.get_by_id.return_value = MagicMock(spec=RoleModel)

    result = service.create_manager_user(
        role_id="role-12345678",
        email="  ADMIN@MNR.LOCAL ",
        password="secure-password",
        full_name=" Administrator ",
        user_status=" ACTIVE ",
    )

    assert result.id == USER_ID
    assert result.email == "admin@mnr.local"
    assert result.password_hash == "hashed:secure-password"
    assert result.user_status is ManagerUserStatus.ACTIVE
    assert result.created_at == NOW
    users.add.assert_called_once_with(result)
    session.flush.assert_called_once_with()
    service.password_hasher.hash_password.assert_called_once_with(
        "secure-password"
    )


def test_create_manager_user_rejects_duplicate_email_and_unknown_role():
    service, _session, users, roles, _user_sessions = build_manager_user_service()
    users.get_by_email.return_value = build_user()
    with pytest.raises(ManagerUserEmailAlreadyExists):
        service.create_manager_user(
            role_id="role-12345678",
            email="admin@mnr.local",
            password="secure-password",
            full_name="Administrator",
        )

    users.get_by_email.return_value = None
    roles.get_by_id.return_value = None
    with pytest.raises(RoleNotFound):
        service.create_manager_user(
            role_id="role-missing",
            email="other@mnr.local",
            password="secure-password",
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


def test_update_manager_user_hashes_password_and_revokes_active_sessions():
    service, session, users, _roles, user_sessions = build_manager_user_service()
    manager_user = build_user()
    users.get_by_id.return_value = manager_user

    result = service.update_manager_user(
        USER_ID,
        password="new-secure-password",
    )

    assert result.password_hash == "hashed:new-secure-password"
    service.password_hasher.hash_password.assert_called_once_with(
        "new-secure-password"
    )
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

    users.get_all.assert_not_called()


def test_list_manager_users_normalizes_search_and_status():
    service, _session, users, _roles, _user_sessions = build_manager_user_service()
    users.get_all.return_value = []

    result = service.list_manager_users(
        offset=10,
        limit=25,
        search="  Admin@MNR.Local  ",
        user_status=" active ",
    )

    assert result == []
    users.get_all.assert_called_once_with(
        offset=10,
        limit=25,
        search="Admin@MNR.Local",
        user_status=ManagerUserStatus.ACTIVE,
    )


@pytest.mark.parametrize("search", ["", "   ", "x" * 256])
def test_list_manager_users_rejects_invalid_search(search):
    service, _session, users, _roles, _user_sessions = build_manager_user_service()

    with pytest.raises(ValueError):
        service.list_manager_users(search=search)

    users.get_all.assert_not_called()


def test_role_service_gets_role_and_permissions():
    roles = MagicMock(spec=RoleRepository)
    permissions = MagicMock(spec=PermissionRepository)
    expected_role = MagicMock(spec=RoleModel)
    expected_permissions = [MagicMock(spec=PermissionModel)]
    roles.get_by_id.return_value = expected_role
    permissions.get_all_by_role_id.return_value = expected_permissions
    service = RoleService(roles, permissions)

    assert service.get_role("role-12345678") is expected_role
    assert service.list_role_permissions("role-12345678") == expected_permissions


def test_role_service_normalizes_search():
    roles = MagicMock(spec=RoleRepository)
    permissions = MagicMock(spec=PermissionRepository)
    roles.get_all.return_value = []
    service = RoleService(roles, permissions)

    assert service.list_roles(search="  Content Editor  ") == []
    roles.get_all.assert_called_once_with(search="Content Editor")


@pytest.mark.parametrize("search", ["", "   ", "x" * 256])
def test_role_service_rejects_invalid_search(search):
    roles = MagicMock(spec=RoleRepository)
    permissions = MagicMock(spec=PermissionRepository)
    service = RoleService(roles, permissions)

    with pytest.raises(ValueError):
        service.list_roles(search=search)

    roles.get_all.assert_not_called()


def test_role_service_raises_domain_error_when_missing():
    roles = MagicMock(spec=RoleRepository)
    permissions = MagicMock(spec=PermissionRepository)
    roles.get_by_id.return_value = None
    service = RoleService(roles, permissions)

    with pytest.raises(RoleNotFound):
        service.get_role("role-missing")


def test_create_role_assigns_permissions_and_audit_fields():
    service, session, roles, permissions, role_permissions = build_role_service()
    roles.get_by_name.return_value = None
    permissions.get_by_id.side_effect = [
        MagicMock(spec=PermissionModel),
        MagicMock(spec=PermissionModel),
    ]

    role = service.create_role(
        name=" Curator ",
        description=" Museum content ",
        permission_ids=["perm-00000001", "perm-00000002"],
        actor_user_id=USER_ID,
    )

    assert role.id == "role-12345678"
    assert role.name == "Curator"
    assert role.description == "Museum content"
    assert role.created_by == USER_ID
    assert role.last_updated_by == USER_ID
    roles.add.assert_called_once_with(role)
    added = [call.args[0] for call in role_permissions.add.call_args_list]
    assert all(isinstance(item, RolePermissionModel) for item in added)
    assert {item.permission_id for item in added} == {
        "perm-00000001",
        "perm-00000002",
    }
    session.flush.assert_called_once_with()


def test_create_role_rejects_duplicate_name():
    service, _session, roles, _permissions, role_permissions = build_role_service()
    roles.get_by_name.return_value = MagicMock(spec=RoleModel)

    with pytest.raises(RoleNameAlreadyExists):
        service.create_role(
            name="System Administrator",
            description=None,
            permission_ids=[],
            actor_user_id=USER_ID,
        )

    role_permissions.add.assert_not_called()


def test_replace_role_permissions_adds_and_removes_atomically():
    service, session, roles, permissions, role_permissions = build_role_service()
    role = MagicMock(spec=RoleModel)
    roles.get_by_id.return_value = role
    permissions.get_by_id.side_effect = [
        MagicMock(spec=PermissionModel),
        MagicMock(spec=PermissionModel),
    ]
    role_permissions.get_all_by_role_id.return_value = [
        RolePermissionModel(
            role_id="role-12345678",
            permission_id="perm-old00001",
        ),
        RolePermissionModel(
            role_id="role-12345678",
            permission_id="perm-00000001",
        ),
    ]
    expected = [MagicMock(spec=PermissionModel)]
    permissions.get_all_by_role_id.return_value = expected

    result = service.replace_role_permissions(
        "role-12345678",
        permission_ids=["perm-00000001", "perm-00000002"],
        actor_user_id=USER_ID,
    )

    assert result == expected
    role_permissions.remove.assert_called_once_with(
        "role-12345678",
        "perm-old00001",
    )
    added = role_permissions.add.call_args.args[0]
    assert added.permission_id == "perm-00000002"
    assert role.last_updated_by == USER_ID
    assert role.last_updated_at == NOW
    session.flush.assert_called_once_with()
