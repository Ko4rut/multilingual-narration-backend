"""Các quy ước HTTP dùng chung cho router của domain Identity."""

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


def set_refresh_cookie(
    response: Response,
    *,
    token: str,
    expires_at: datetime,
    settings: Settings,
) -> None:
    """Đặt Refresh Token sao cho JavaScript phía trình duyệt không đọc được."""

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
    """Xóa Refresh Token bằng đúng thuộc tính path/domain lúc tạo cookie."""

    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        path=settings.auth_cookie_path,
        domain=settings.auth_cookie_domain,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )


def remaining_seconds(expires_at: datetime) -> int:
    """Chuyển thời điểm hết hạn thành số giây dương dùng cho HTTP response."""

    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise ValueError("expires_at must include timezone information")
    remaining = expires_at.astimezone(timezone.utc) - datetime.now(timezone.utc)
    return max(1, int(remaining.total_seconds()))


def raise_unauthorized(exc: Exception | None = None) -> None:
    """Chuẩn hóa lỗi xác thực và không làm lộ nguyên nhân nội bộ cho client."""

    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if exc is None:
        raise error
    raise error from exc
