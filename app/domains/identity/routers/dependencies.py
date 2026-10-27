"""FastAPI dependencies dùng để lắp ghép các thành phần của domain Identity."""

from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domains.identity.repositories.manager_user import ManagerUserRepository
from app.domains.identity.repositories.permission import PermissionRepository
from app.domains.identity.repositories.user_session import UserSessionRepository
from app.domains.identity.routers.http import (
    AUTHENTICATION_ERRORS,
    raise_unauthorized,
)
from app.domains.identity.security.jwt import JwtAccessTokenProvider
from app.domains.identity.security.password import Argon2PasswordProvider
from app.domains.identity.security.refresh_token import SecureRefreshTokenProvider
from app.domains.identity.services.identity import (
    AuthenticatedIdentity,
    IdentityService,
)
from app.route.dependencies import get_session


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_password_provider() -> Argon2PasswordProvider:
    """Dùng chung cấu hình Argon2 và dummy hash giữa các request."""

    return Argon2PasswordProvider()


@lru_cache
def get_refresh_token_provider() -> SecureRefreshTokenProvider:
    """Tạo provider sinh Refresh Token ngẫu nhiên có độ dài an toàn."""

    return SecureRefreshTokenProvider()


def get_access_token_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JwtAccessTokenProvider:
    """Khởi tạo JWT provider từ khóa bí mật của môi trường triển khai."""

    if settings.jwt_private_key is None or not settings.jwt_public_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT signing keys are not configured",
        )
    try:
        return JwtAccessTokenProvider(
            private_key=settings.jwt_private_key.get_secret_value(),
            public_keys=settings.jwt_public_keys,
            active_key_id=settings.jwt_active_key_id,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            access_token_ttl=timedelta(
                seconds=settings.access_token_ttl_seconds
            ),
            leeway=timedelta(seconds=settings.jwt_leeway_seconds),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT signing keys are invalid",
        ) from exc


def get_identity_service(
    session: Annotated[Session, Depends(get_session)],
    password_provider: Annotated[
        Argon2PasswordProvider,
        Depends(get_password_provider),
    ],
    access_token_provider: Annotated[
        JwtAccessTokenProvider,
        Depends(get_access_token_provider),
    ],
    refresh_token_provider: Annotated[
        SecureRefreshTokenProvider,
        Depends(get_refresh_token_provider),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IdentityService:
    """Ghép service với cùng một Session để bảo toàn ranh giới giao dịch."""

    return IdentityService(
        session=session,
        manager_user_repository=ManagerUserRepository(session),
        user_session_repository=UserSessionRepository(session),
        permission_repository=PermissionRepository(session),
        password_provider=password_provider,
        access_token_provider=access_token_provider,
        refresh_token_provider=refresh_token_provider,
        refresh_token_ttl=timedelta(
            seconds=settings.refresh_token_ttl_seconds
        ),
    )


def get_current_identity(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> AuthenticatedIdentity:
    """Xác thực Bearer token và đối chiếu phiên đang lưu trong cơ sở dữ liệu."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise_unauthorized()
    try:
        return service.authenticate_access_token(credentials.credentials)
    except AUTHENTICATION_ERRORS as exc:
        raise_unauthorized(exc)
