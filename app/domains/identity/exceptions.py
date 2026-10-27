from app.core.exceptions import ResourceNotFound


class ManagerUserNotFound(ResourceNotFound):
    """The requested manager user does not exist."""


class RoleNotFound(ResourceNotFound):
    """The requested role does not exist."""


class ManagerUserEmailAlreadyExists(Exception):
    """A manager user already uses the requested email address."""


class InvalidCredentials(Exception):
    """The supplied email or password is invalid."""


class InvalidAccessToken(Exception):
    """The supplied access token cannot authenticate a request."""


class InactiveManagerUser(Exception):
    """The manager user is not allowed to authenticate."""


class UserSessionNotFound(ResourceNotFound):
    """The requested user session does not exist."""


class UserSessionExpired(Exception):
    """The user session has expired."""


class UserSessionRevoked(Exception):
    """The user session has already been revoked."""


class RefreshTokenAlreadyExists(Exception):
    """A user session already uses the refresh-token hash."""
