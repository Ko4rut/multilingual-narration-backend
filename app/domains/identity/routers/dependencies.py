"""FastAPI dependencies lắp ghép repository và service của Identity."""

from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domains.identity.repositories.manager_user import ManagerUserRepository
from app.domains.identity.repositories.permission import PermissionRepository
from app.domains.identity.repositories.role import RoleRepository
from app.domains.identity.repositories.role_permission import RolePermissionRepository
from app.domains.identity.repositories.user_session import UserSessionRepository
from app.domains.identity.routers.http import (
    AUTHENTICATION_ERRORS,
    raise_unauthorized,
)
from app.domains.identity.security import (
    Argon2PasswordHasher,
    JwtAccessTokenSigner,
    SecureRefreshTokenManager,
)
from app.domains.identity.services.authentication import (
    AuthenticationService,
    AuthenticatedIdentity,
)
from app.domains.identity.services.manager_user import ManagerUserService
from app.domains.identity.services.role import RoleService
from app.route.dependencies import get_session


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_password_hasher() -> Argon2PasswordHasher:
    """Dùng lại cấu hình Argon2 và dummy hash giữa các request."""
    return Argon2PasswordHasher()


@lru_cache
def get_refresh_token_manager() -> SecureRefreshTokenManager:
    """Dùng bộ sinh Refresh Token entropy cao cho mọi request."""
    return SecureRefreshTokenManager()


def get_access_token_signer(settings: Annotated[Settings, Depends(get_settings)]) -> JwtAccessTokenSigner:
    """Dựng bộ ký JWT từ khóa được inject qua cấu hình triển khai."""

    if settings.jwt_private_key is None or not settings.jwt_public_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT signing keys are not configured",
        )
    try:
        return JwtAccessTokenSigner(
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


def get_authentication_service(
    session: Annotated[Session, Depends(get_session)],
    password_hasher: Annotated[Argon2PasswordHasher, Depends(get_password_hasher)],
    access_token_signer: Annotated[JwtAccessTokenSigner, Depends(get_access_token_signer)],
    refresh_token_manager: Annotated[SecureRefreshTokenManager, Depends(get_refresh_token_manager)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticationService:
    """Inject các dependency cần thiết cho AuthenticationService."""

    return AuthenticationService(
        session=session,
        manager_user_repository=ManagerUserRepository(session),
        user_session_repository=UserSessionRepository(session),
        permission_repository=PermissionRepository(session),
        password_hasher=password_hasher,
        access_token_signer=access_token_signer,
        refresh_token_manager=refresh_token_manager,
        refresh_token_ttl=timedelta(
            seconds=settings.refresh_token_ttl_seconds
        ),
    )


def get_current_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> AuthenticatedIdentity:
    """Đọc Bearer token rồi xác minh JWT và trạng thái tài khoản hiện tại."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise_unauthorized()
    try:
        return service.authenticate_access_token(credentials.credentials)
    except AUTHENTICATION_ERRORS as exc:
        raise_unauthorized(exc)


def get_manager_user_service(
    # Session nghiệp vụ tách khỏi Session đã dùng để xác thực/RBAC, tránh
    # transaction ngầm của truy vấn auth bao lấy write transaction.
    session: Annotated[Session, Depends(get_session, use_cache=False)],
    password_hasher: Annotated[Argon2PasswordHasher, Depends(get_password_hasher)],
) -> ManagerUserService:
    return ManagerUserService(
        session=session,
        manager_user_repository=ManagerUserRepository(session),
        role_repository=RoleRepository(session),
        user_session_repository=UserSessionRepository(session),
        password_hasher=password_hasher,
    )


def get_role_service(session: Annotated[Session, Depends(get_session, use_cache=False)]) -> RoleService:
    return RoleService(
        role_repository=RoleRepository(session),
        permission_repository=PermissionRepository(session),
        session=session,
        role_permission_repository=RolePermissionRepository(session),
    )


def require_user_management(action_name: str):
    """Tạo dependency RBAC cho một hành động thuộc User Management."""

    def check_permission(
        identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
        service: Annotated[AuthenticationService, Depends(get_authentication_service)],
    ) -> AuthenticatedIdentity:
        if not service.has_permission(
            identity.manager_user.id,
            function_name="User Management",
            action_name=action_name,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission",
            )
        return identity
    return check_permission


require_user_management_read = require_user_management("read")
require_user_management_create = require_user_management("create")
require_user_management_update = require_user_management("update")
