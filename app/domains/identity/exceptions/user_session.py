from app.core.exceptions import ResourceNotFound


class UserSessionNotFound(ResourceNotFound):
    """Không tìm thấy phiên người dùng được yêu cầu."""


class UserSessionExpired(Exception):
    """Phiên người dùng đã hết hạn."""


class UserSessionRevoked(Exception):
    """Phiên người dùng đã bị thu hồi."""


class RefreshTokenAlreadyExists(Exception):
    """Một phiên khác đã sử dụng Refresh Token hash này."""
