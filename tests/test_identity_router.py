from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError
from starlette.requests import Request

from app.core.config import Settings
from app.domains.identity.exceptions import InvalidCredentials
from app.domains.identity.models.manager_user import ManagerUserStatus
from app.domains.identity.routers.dependencies import (
    get_access_token_signer,
    get_current_identity,
    require_user_management_read,
)
from app.domains.identity.routers.identity import (
    create_manager_user,
    get_me,
    list_manager_users,
    list_roles,
    login,
    logout,
    refresh_access_token,
    update_manager_user,
)
from app.domains.identity.schemas.authentication import LoginRequest
from app.domains.identity.schemas.manager_user import (
    ManagerUserCreate,
    ManagerUserUpdate,
)
from app.main import create_app


NOW = datetime.now(timezone.utc)


def _settings(**overrides: object) -> Settings:
    required_settings = {
        "database_url": "postgresql+psycopg://test:test@localhost:5433/test",
        "jwt_active_key_id": "test-key-1",
        "jwt_issuer": "test-issuer",
        "jwt_audience": "test-audience",
        "auth_cookie_secure": True,
    }
    required_settings.update(overrides)
    return Settings(_env_file=None, **required_settings)


def _manager_user() -> SimpleNamespace:
    return SimpleNamespace(
        id="user-281026-12345678",
        role_id="role-12345678",
        email="admin@example.com",
        full_name="Admin",
        user_status=ManagerUserStatus.ACTIVE,
        created_at=NOW,
        last_updated_at=NOW,
        last_login_at=NOW,
    )


def _role() -> SimpleNamespace:
    return SimpleNamespace(
        id="role-12345678",
        name="Content Editor",
        description="Manages narration content",
        created_by="user-281026-12345678",
        last_updated_by="user-281026-12345678",
        created_at=NOW,
        last_updated_at=NOW,
    )


def _request(cookie: str | None = None) -> Request:
    headers = [] if cookie is None else [(b"cookie", cookie.encode())]
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": headers,
            "query_string": b"",
            "scheme": "https",
            "server": ("testserver", 443),
            "client": ("testclient", 50000),
        }
    )


class AuthenticationServiceStub:
    def __init__(self) -> None:
        self.login_arguments: tuple[str, str] | None = None
        self.refreshed_token: str | None = None
        self.logged_out_token: str | None = None
        self.access_token: str | None = None
        self.login_error: Exception | None = None

    def login(
        self,
        *,
        email: str,
        password: str,
    ) -> SimpleNamespace:
        if self.login_error is not None:
            raise self.login_error
        self.login_arguments = (email, password)
        return SimpleNamespace(
            manager_user=_manager_user(),
            user_session=SimpleNamespace(expires_at=NOW + timedelta(days=30)),
            access_token=SimpleNamespace(
                token="signed-access-token",
                expires_at=NOW + timedelta(minutes=15),
            ),
            refresh_token="opaque-refresh-token",
        )

    def refresh(self, token: str) -> SimpleNamespace:
        self.refreshed_token = token
        return SimpleNamespace(
            user_session=SimpleNamespace(expires_at=NOW + timedelta(days=30)),
            access_token=SimpleNamespace(
                token="rotated-access-token",
                expires_at=NOW + timedelta(minutes=15),
            ),
            refresh_token="rotated-refresh-token",
        )

    def logout(self, token: str) -> None:
        self.logged_out_token = token

    def authenticate_access_token(self, token: str) -> SimpleNamespace:
        self.access_token = token
        return SimpleNamespace(manager_user=_manager_user())

    def has_permission(self, user_id: str, **kwargs: str) -> bool:
        return True


class ManagerUserServiceStub:
    def __init__(self) -> None:
        self.password: str | None = None
        self.list_filters: dict[str, object] | None = None
        self.updated_values: dict[str, object] | None = None

    def list_manager_users(self, **filters: object) -> list[SimpleNamespace]:
        self.list_filters = filters
        return [_manager_user()]

    def create_manager_user(self, **values: object) -> SimpleNamespace:
        self.password = str(values["password"])
        return _manager_user()

    def update_manager_user(
        self,
        _user_id: str,
        **values: object,
    ) -> SimpleNamespace:
        self.updated_values = values
        return _manager_user()


class RoleServiceStub:
    def __init__(self) -> None:
        self.search: str | None = None

    def list_roles(self, *, search: str | None = None) -> list[SimpleNamespace]:
        self.search = search
        return [_role()]


def test_login_returns_token_and_sets_secure_httponly_cookie() -> None:
    service = AuthenticationServiceStub()
    response = Response()

    result = login(
        LoginRequest(email="admin@example.com", password="secret"),
        response,
        service,
        _settings(),
    )

    assert result.access_token == "signed-access-token"
    assert result.user.id == "user-281026-12345678"
    assert service.login_arguments == ("admin@example.com", "secret")
    cookie = response.headers["set-cookie"]
    assert "opaque-refresh-token" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/api/v1/auth" in cookie


def test_login_maps_invalid_credentials_to_generic_unauthorized() -> None:
    service = AuthenticationServiceStub()
    service.login_error = InvalidCredentials("invalid email or password")

    with pytest.raises(HTTPException) as exc_info:
        login(
            LoginRequest(email="admin@example.com", password="wrong"),
            Response(),
            service,
            _settings(),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authentication required"


@pytest.mark.parametrize(
    ("schema", "values"),
    [
        (
            LoginRequest,
            {"email": "admin@example.com", "password": "invalid password"},
        ),
        (
            ManagerUserCreate,
            {
                "role_id": "role-12345678",
                "email": "admin@example.com",
                "password": "invalid\tpassword",
                "full_name": "Admin",
            },
        ),
        (ManagerUserUpdate, {"password": "invalid\npassword"}),
    ],
)
def test_identity_password_schemas_reject_whitespace(schema, values) -> None:
    with pytest.raises(ValidationError, match="password must not contain whitespace"):
        schema(**values)


def test_refresh_rotates_cookie_without_exposing_refresh_token() -> None:
    service = AuthenticationServiceStub()
    response = Response()

    result = refresh_access_token(
        _request("refresh_token=old-refresh-token"),
        response,
        service,
        _settings(),
    )

    assert result.access_token == "rotated-access-token"
    assert service.refreshed_token == "old-refresh-token"
    assert "rotated-refresh-token" in response.headers["set-cookie"]
    assert "refresh_token" not in result.model_dump()


def test_logout_revokes_session_and_deletes_cookie() -> None:
    service = AuthenticationServiceStub()
    response = Response()

    logout(
        _request("refresh_token=current-refresh-token"),
        response,
        service,
        _settings(),
    )

    assert service.logged_out_token == "current-refresh-token"
    cookie = response.headers["set-cookie"]
    assert "refresh_token=\"\"" in cookie
    assert "Max-Age=0" in cookie


def test_me_and_bearer_dependency_only_return_public_user() -> None:
    service = AuthenticationServiceStub()
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="signed-access-token",
    )

    identity = get_current_identity(credentials, service)
    result = get_me(identity)

    assert service.access_token == "signed-access-token"
    assert result.id == "user-281026-12345678"
    assert "password_hash" not in result.model_dump()


def test_missing_bearer_token_is_unauthorized() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_current_identity(None, AuthenticationServiceStub())

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_missing_jwt_keys_reports_service_unavailable() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_access_token_signer(_settings())

    assert exc_info.value.status_code == 503


def test_all_authentication_routes_are_registered() -> None:
    paths = create_app().openapi()["paths"]

    assert "post" in paths["/api/v1/auth/login"]
    assert "post" in paths["/api/v1/auth/refresh"]
    assert "post" in paths["/api/v1/auth/logout"]
    assert "get" in paths["/api/v1/auth/me"]
    assert paths["/api/v1/auth/me"]["get"]["security"] == [
        {"HTTPBearer": []}
    ]


def test_manager_user_creation_passes_plaintext_only_to_service() -> None:
    service = ManagerUserServiceStub()
    identity = SimpleNamespace(manager_user=_manager_user())

    result = create_manager_user(
        ManagerUserCreate(
            role_id="role-12345678",
            email="admin@example.com",
            password="new-secret-password",
            full_name="Admin",
        ),
        identity,
        service,
    )

    assert result.id == "user-281026-12345678"
    assert service.password == "new-secret-password"
    assert "password_hash" not in result.model_dump()


def test_manager_user_list_passes_search_status_and_pagination() -> None:
    service = ManagerUserServiceStub()
    identity = SimpleNamespace(manager_user=_manager_user())

    result = list_manager_users(
        identity,
        service,
        offset=20,
        limit=10,
        search="admin",
        user_status=ManagerUserStatus.ACTIVE,
    )

    assert [user.id for user in result] == ["user-281026-12345678"]
    assert service.list_filters == {
        "offset": 20,
        "limit": 10,
        "search": "admin",
        "user_status": ManagerUserStatus.ACTIVE,
    }


def test_manager_user_update_passes_password_value_to_service() -> None:
    service = ManagerUserServiceStub()
    identity = SimpleNamespace(manager_user=_manager_user())

    result = update_manager_user(
        "user-281026-12345678",
        ManagerUserUpdate(
            full_name="Updated Admin",
            password="replacement-password",
        ),
        identity,
        service,
    )

    assert result.id == "user-281026-12345678"
    assert service.updated_values is not None
    assert service.updated_values["password"] == "replacement-password"
    assert "password_hash" not in result.model_dump()


def test_role_list_passes_search_to_service() -> None:
    service = RoleServiceStub()
    identity = SimpleNamespace(manager_user=_manager_user())

    result = list_roles(identity, service, search="content")

    assert [role.id for role in result] == ["role-12345678"]
    assert service.search == "content"


def test_user_management_dependency_returns_403_without_permission() -> None:
    service = AuthenticationServiceStub()
    service.has_permission = lambda *args, **kwargs: False
    identity = SimpleNamespace(manager_user=_manager_user())

    with pytest.raises(HTTPException) as exc_info:
        require_user_management_read(identity, service)

    assert exc_info.value.status_code == 403


def test_manager_user_and_role_routes_are_registered() -> None:
    paths = create_app().openapi()["paths"]

    expected_methods = {
        "/api/v1/manager-users": {"get", "post"},
        "/api/v1/manager-users/{user_id}": {"get", "patch"},
        "/api/v1/roles": {"get", "post"},
        "/api/v1/roles/{role_id}": {"get", "patch"},
        "/api/v1/roles/{role_id}/permissions": {"get", "put"},
        "/api/v1/roles/permissions": {"get"},
    }
    for path, methods in expected_methods.items():
        assert set(paths[path]) >= methods
