from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

from app.core.config import Settings
from app.domains.identity.models.manager_user import ManagerUserStatus
from app.domains.identity.routers.dependencies import (
    get_access_token_provider,
    get_current_identity,
)
from app.domains.identity.routers.identity import (
    get_me,
    login,
    logout,
    refresh_access_token,
)
from app.domains.identity.schemas.authentication import LoginRequest


NOW = datetime.now(timezone.utc)


def _settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        auth_cookie_secure=True,
        **overrides,
    )


def _manager_user() -> SimpleNamespace:
    return SimpleNamespace(
        id="user-271026-12345678",
        role_id="role-12345678",
        email="admin@example.com",
        full_name="Admin",
        user_status=ManagerUserStatus.ACTIVE,
        created_at=NOW,
        last_updated_at=NOW,
        last_login_at=NOW,
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


class IdentityServiceStub:
    def __init__(self) -> None:
        self.login_arguments: tuple[str, str] | None = None
        self.refreshed_token: str | None = None
        self.logged_out_token: str | None = None

    def login(self, *, email: str, password: str) -> SimpleNamespace:
        self.login_arguments = (email, password)
        return SimpleNamespace(
            manager_user=_manager_user(),
            user_session=SimpleNamespace(expires_at=NOW + timedelta(days=1)),
            access_token=SimpleNamespace(
                token="signed-access-token",
                expires_at=NOW + timedelta(minutes=15),
            ),
            refresh_token="opaque-refresh-token",
        )

    def refresh(self, token: str) -> SimpleNamespace:
        self.refreshed_token = token
        return SimpleNamespace(
            user_session=SimpleNamespace(expires_at=NOW + timedelta(days=1)),
            access_token=SimpleNamespace(
                token="rotated-access-token",
                expires_at=NOW + timedelta(minutes=15),
            ),
            refresh_token="rotated-refresh-token",
        )

    def logout(self, token: str) -> None:
        self.logged_out_token = token


def test_login_returns_access_token_and_sets_httponly_cookie() -> None:
    service = IdentityServiceStub()
    response = Response()

    result = login(
        LoginRequest(email="admin@example.com", password="secret"),
        response,
        service,
        _settings(),
    )

    assert result.access_token == "signed-access-token"
    assert result.user.id == "user-271026-12345678"
    assert service.login_arguments == ("admin@example.com", "secret")
    cookie = response.headers["set-cookie"]
    assert "opaque-refresh-token" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/api/v1/identity" in cookie


def test_refresh_rotates_cookie_without_returning_refresh_token() -> None:
    service = IdentityServiceStub()
    response = Response()

    result = refresh_access_token(
        _request("refresh_token=old-refresh-token"),
        response,
        service,
        _settings(),
    )

    assert result.model_dump() == {
        "access_token": "rotated-access-token",
        "token_type": "Bearer",
        "expires_in": result.expires_in,
    }
    assert service.refreshed_token == "old-refresh-token"
    assert "rotated-refresh-token" in response.headers["set-cookie"]


def test_logout_revokes_session_and_deletes_cookie() -> None:
    service = IdentityServiceStub()
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


def test_me_only_exposes_public_manager_user_fields() -> None:
    identity = SimpleNamespace(manager_user=_manager_user())

    result = get_me(identity)

    assert result.id == "user-271026-12345678"
    assert "password_hash" not in result.model_dump()


def test_missing_bearer_token_is_unauthorized() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_current_identity(None, IdentityServiceStub())

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_missing_jwt_keys_reports_service_unavailable() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_access_token_provider(_settings())

    assert exc_info.value.status_code == 503
