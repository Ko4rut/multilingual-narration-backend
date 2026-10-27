"""Business exception được công khai bởi domain Identity."""

from app.domains.identity.exceptions.authentication import (
    InvalidAccessToken,
    InvalidCredentials,
)
from app.domains.identity.exceptions.manager_user import (
    InactiveManagerUser,
    ManagerUserEmailAlreadyExists,
    ManagerUserNotFound,
)
from app.domains.identity.exceptions.role import RoleNotFound
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
    "RefreshTokenAlreadyExists",
    "RoleNotFound",
    "UserSessionExpired",
    "UserSessionNotFound",
    "UserSessionRevoked",
]
