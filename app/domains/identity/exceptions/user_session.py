from app.core.exceptions import ResourceNotFound


class UserSessionNotFound(ResourceNotFound):
    """Không tìm thấy phiên tương ứng với token được cung cấp."""


class UserSessionExpired(Exception):
    """Phiên đăng nhập đã hết hạn."""


class UserSessionRevoked(Exception):
    """Phiên đăng nhập đã bị thu hồi."""


class RefreshTokenAlreadyExists(Exception):
    """Refresh Token hash vừa sinh đã trùng với một session khác."""
