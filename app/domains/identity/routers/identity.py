"""HTTP controller mỏng cho đăng nhập, refresh, đăng xuất và current user."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)

from app.core.config import Settings, get_settings
from app.domains.identity.exceptions import (
    ManagerUserEmailAlreadyExists,
    RefreshTokenAlreadyExists,
    RoleNameAlreadyExists,
    UserSessionNotFound,
)
from app.domains.identity.routers.dependencies import (
    get_current_identity,
    get_identity_service,
    get_manager_user_service,
    get_role_service,
    require_user_management_create,
    require_user_management_read,
    require_user_management_update,
)
from app.domains.identity.routers.http import (
    AUTHENTICATION_ERRORS,
    delete_refresh_cookie,
    remaining_seconds,
    raise_unauthorized,
    set_refresh_cookie,
)
from app.domains.identity.schemas.authentication import (
    AccessTokenResponse,
    LoginRequest,
    LoginResponse,
)
from app.domains.identity.schemas.manager_user import (
    ManagerUserCreate,
    ManagerUserRead,
    ManagerUserUpdate,
)
from app.domains.identity.schemas.permission import PermissionRead
from app.domains.identity.schemas.role import (
    RoleCreate,
    RolePermissionsUpdate,
    RoleRead,
    RoleUpdate,
)
from app.domains.identity.services.identity import (
    AuthenticatedIdentity,
    IdentityService,
    ManagerUserService,
    RoleService,
)


router = APIRouter(prefix="/identity", tags=["Identity"])

UserManagementRead = Annotated[
    AuthenticatedIdentity,
    Depends(require_user_management_read),
]
UserManagementCreate = Annotated[
    AuthenticatedIdentity,
    Depends(require_user_management_create),
]
UserManagementUpdate = Annotated[
    AuthenticatedIdentity,
    Depends(require_user_management_update),
]


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    """Tạo session, trả Access Token và đặt Refresh Token HttpOnly."""

    try:
        result = service.authenticate_and_issue_access_token(
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
    """Xoay Refresh Token cookie và cấp Access Token mới."""

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
    """Thu hồi session hiện tại và luôn xóa Refresh Token cookie."""

    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if refresh_token:
        try:
            service.logout(refresh_token)
        except UserSessionNotFound:
            # Logout idempotent: cookie cũ vẫn bị xóa nếu session đã mất.
            pass
    delete_refresh_cookie(response, settings)


@router.get("/me", response_model=ManagerUserRead)
def get_me(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(get_current_identity),
    ],
) -> ManagerUserRead:
    """Trả thông tin công khai của chủ sở hữu Access Token hiện tại."""

    return ManagerUserRead.model_validate(identity.manager_user)


@router.get("/manager-users", response_model=list[ManagerUserRead])
def list_manager_users(
    _identity: UserManagementRead,
    service: Annotated[ManagerUserService, Depends(get_manager_user_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ManagerUserRead]:
    return [
        ManagerUserRead.model_validate(user)
        for user in service.list_manager_users(offset=offset, limit=limit)
    ]


@router.post(
    "/manager-users",
    response_model=ManagerUserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_manager_user(
    payload: ManagerUserCreate,
    _identity: UserManagementCreate,
    service: Annotated[ManagerUserService, Depends(get_manager_user_service)],
) -> ManagerUserRead:
    try:
        user = service.create_manager_user(
            role_id=payload.role_id,
            email=payload.email,
            password=payload.password.get_secret_value(),
            full_name=payload.full_name,
            user_status=payload.user_status,
        )
    except ManagerUserEmailAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ManagerUserRead.model_validate(user)


@router.get("/manager-users/{user_id}", response_model=ManagerUserRead)
def get_manager_user(
    user_id: Annotated[str, Path(min_length=1, max_length=50)],
    _identity: UserManagementRead,
    service: Annotated[ManagerUserService, Depends(get_manager_user_service)],
) -> ManagerUserRead:
    return ManagerUserRead.model_validate(service.get_manager_user(user_id))


@router.patch("/manager-users/{user_id}", response_model=ManagerUserRead)
def update_manager_user(
    user_id: Annotated[str, Path(min_length=1, max_length=50)],
    payload: ManagerUserUpdate,
    _identity: UserManagementUpdate,
    service: Annotated[ManagerUserService, Depends(get_manager_user_service)],
) -> ManagerUserRead:
    try:
        user = service.update_manager_user(
            user_id,
            role_id=payload.role_id,
            email=payload.email,
            full_name=payload.full_name,
            user_status=payload.user_status,
            password=(
                payload.password.get_secret_value()
                if payload.password is not None
                else None
            ),
        )
    except ManagerUserEmailAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ManagerUserRead.model_validate(user)


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    _identity: UserManagementRead,
    service: Annotated[RoleService, Depends(get_role_service)],
) -> list[RoleRead]:
    return [RoleRead.model_validate(role) for role in service.list_roles()]


@router.post(
    "/roles",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_role(
    payload: RoleCreate,
    identity: UserManagementCreate,
    service: Annotated[RoleService, Depends(get_role_service)],
) -> RoleRead:
    try:
        role = service.create_role(
            name=payload.name,
            description=payload.description,
            permission_ids=payload.permission_ids,
            actor_user_id=identity.manager_user.id,
        )
    except RoleNameAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RoleRead.model_validate(role)


@router.get("/roles/{role_id}", response_model=RoleRead)
def get_role(
    role_id: Annotated[str, Path(min_length=1, max_length=50)],
    _identity: UserManagementRead,
    service: Annotated[RoleService, Depends(get_role_service)],
) -> RoleRead:
    return RoleRead.model_validate(service.get_role(role_id))


@router.patch("/roles/{role_id}", response_model=RoleRead)
def update_role(
    role_id: Annotated[str, Path(min_length=1, max_length=50)],
    payload: RoleUpdate,
    identity: UserManagementUpdate,
    service: Annotated[RoleService, Depends(get_role_service)],
) -> RoleRead:
    try:
        role = service.update_role(
            role_id,
            actor_user_id=identity.manager_user.id,
            name=payload.name,
            description=payload.description,
            update_description="description" in payload.model_fields_set,
        )
    except RoleNameAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RoleRead.model_validate(role)


@router.get("/roles/{role_id}/permissions", response_model=list[PermissionRead])
def list_role_permissions(
    role_id: Annotated[str, Path(min_length=1, max_length=50)],
    _identity: UserManagementRead,
    service: Annotated[RoleService, Depends(get_role_service)],
) -> list[PermissionRead]:
    return [
        PermissionRead.model_validate(permission)
        for permission in service.list_role_permissions(role_id)
    ]


@router.put("/roles/{role_id}/permissions", response_model=list[PermissionRead])
def replace_role_permissions(
    role_id: Annotated[str, Path(min_length=1, max_length=50)],
    payload: RolePermissionsUpdate,
    identity: UserManagementUpdate,
    service: Annotated[RoleService, Depends(get_role_service)],
) -> list[PermissionRead]:
    permissions = service.replace_role_permissions(
        role_id,
        permission_ids=payload.permission_ids,
        actor_user_id=identity.manager_user.id,
    )
    return [PermissionRead.model_validate(permission) for permission in permissions]


@router.get("/permissions", response_model=list[PermissionRead])
def list_permissions(
    _identity: UserManagementRead,
    service: Annotated[RoleService, Depends(get_role_service)],
) -> list[PermissionRead]:
    return [
        PermissionRead.model_validate(permission)
        for permission in service.list_permissions()
    ]
