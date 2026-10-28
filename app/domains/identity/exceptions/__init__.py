"""Business exception được công khai bởi domain Identity."""

from app.domains.identity.exceptions.authentication import InvalidAccessToken
from app.domains.identity.exceptions.manager_user import (
    InactiveManagerUser,
    InvalidCredentials,
    ManagerUserEmailAlreadyExists,
    ManagerUserNotFound,
)
from app.domains.identity.exceptions.role import (
    PermissionNotFound,
    RoleNameAlreadyExists,
    RoleNotFound,
)
from app.domains.identity.exceptions.user_session import (
    RefreshTokenAlreadyExists,
    UserSessionExpired,
    UserSessionNotFound,
    UserSessionRevoked,
)

__all__ = [
    "InactiveManagerUser",
    "InvalidAccessToken",
    "InvalidCredentials",
    "ManagerUserEmailAlreadyExists",
    "ManagerUserNotFound",
    "PermissionNotFound",
    "RoleNameAlreadyExists",
    "RoleNotFound",
    "RefreshTokenAlreadyExists",
    "UserSessionExpired",
    "UserSessionNotFound",
    "UserSessionRevoked",
]
