"""Các HTTP endpoint cho quy trình đăng nhập và quản lý phiên Identity."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.config import Settings, get_settings
from app.domains.identity.exceptions import (
    RefreshTokenAlreadyExists,
    UserSessionNotFound,
)
from app.domains.identity.routers.dependencies import (
    get_current_identity,
    get_identity_service,
)
from app.domains.identity.routers.http import (
    AUTHENTICATION_ERRORS,
    delete_refresh_cookie,
    raise_unauthorized,
    remaining_seconds,
    set_refresh_cookie,
)
from app.domains.identity.schemas.authentication import (
    AccessTokenResponse,
    LoginRequest,
    LoginResponse,
)
from app.domains.identity.schemas.manager_user import ManagerUserRead
from app.domains.identity.services.identity import (
    AuthenticatedIdentity,
    IdentityService,
)


router = APIRouter(prefix="/identity", tags=["Identity"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    """Đăng nhập, trả Access Token và đặt Refresh Token vào cookie HttpOnly."""

    try:
        result = service.login(
            email=payload.email,
            password=payload.password.get_secret_value(),
        )
    except AUTHENTICATION_ERRORS as exc:
        raise_unauthorized(exc)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RefreshTokenAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create a unique session",
        ) from exc

    set_refresh_cookie(
        response,
        token=result.refresh_token,
        expires_at=result.user_session.expires_at,
        settings=settings,
    )
    return LoginResponse(
        access_token=result.access_token.token,
        expires_in=remaining_seconds(result.access_token.expires_at),
        user=ManagerUserRead.model_validate(result.manager_user),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_access_token(
    request: Request,
    response: Response,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AccessTokenResponse:
    """Xoay vòng Refresh Token và cấp Access Token mới cho phiên hợp lệ."""

    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if not refresh_token:
        raise_unauthorized()
    try:
        result = service.refresh(refresh_token)
    except AUTHENTICATION_ERRORS as exc:
        raise_unauthorized(exc)
    except RefreshTokenAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to rotate refresh token",
        ) from exc

    set_refresh_cookie(
        response,
        token=result.refresh_token,
        expires_at=result.user_session.expires_at,
        settings=settings,
    )
    return AccessTokenResponse(
        access_token=result.access_token.token,
        expires_in=remaining_seconds(result.access_token.expires_at),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Thu hồi phiên nếu còn tồn tại và luôn xóa Refresh Token phía trình duyệt."""

    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if refresh_token:
        try:
            service.logout(refresh_token)
        except UserSessionNotFound:
            # Logout mang tính idempotent: cookie cũ vẫn được xóa dù phiên đã mất.
            pass
    delete_refresh_cookie(response, settings)


@router.get("/me", response_model=ManagerUserRead)
def get_me(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(get_current_identity),
    ],
) -> ManagerUserRead:
    """Trả thông tin công khai của người dùng sở hữu Access Token hiện tại."""

    return ManagerUserRead.model_validate(identity.manager_user)
