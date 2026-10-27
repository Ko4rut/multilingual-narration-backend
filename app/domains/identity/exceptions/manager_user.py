from app.core.exceptions import ResourceNotFound


class ManagerUserNotFound(ResourceNotFound):
    """Không tìm thấy người dùng quản trị được yêu cầu."""


class ManagerUserEmailAlreadyExists(Exception):
    """Email đã được một người dùng quản trị khác sử dụng."""


class InactiveManagerUser(Exception):
    """Người dùng quản trị không được phép xác thực vì không hoạt động."""
