"""Quy ước lỗi và cookie xác thực của domain Identity."""

from datetime import datetime, timezone

from fastapi import HTTPException, Response, status

from app.core.config import Settings
from app.domains.identity.exceptions import (
    InactiveManagerUser,
    InvalidAccessToken,
    InvalidCredentials,
    ManagerUserNotFound,
    UserSessionExpired,
    UserSessionNotFound,
    UserSessionRevoked,
)


AUTHENTICATION_ERRORS = (
    InvalidCredentials,
    InvalidAccessToken,
    InactiveManagerUser,
    ManagerUserNotFound,
    UserSessionNotFound,
    UserSessionExpired,
    UserSessionRevoked,
)


def remaining_seconds(expires_at: datetime) -> int:
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise ValueError("expires_at must include timezone information")
    remaining = expires_at.astimezone(timezone.utc) - datetime.now(timezone.utc)
    return max(1, int(remaining.total_seconds()))


def set_refresh_cookie(
    response: Response,
    *,
    token: str,
    expires_at: datetime,
    settings: Settings,
) -> None:
    """Đặt Refresh Token trong cookie mà JavaScript không thể đọc."""

    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=token,
        max_age=remaining_seconds(expires_at),
        expires=expires_at,
        path=settings.auth_cookie_path,
        domain=settings.auth_cookie_domain,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )


def delete_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        path=settings.auth_cookie_path,
        domain=settings.auth_cookie_domain,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )


def raise_unauthorized(exc: Exception | None = None) -> None:
    """Trả một lỗi chung để không tiết lộ email, trạng thái hay nội dung JWT."""

    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if exc is None:
        raise error
    raise error from exc
