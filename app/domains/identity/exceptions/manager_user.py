from app.core.exceptions import ResourceNotFound


class ManagerUserNotFound(ResourceNotFound):
    """Không tìm thấy người dùng quản trị được yêu cầu."""


class ManagerUserEmailAlreadyExists(Exception):
    """Email đã được một người dùng quản trị khác sử dụng."""


class InvalidCredentials(Exception):
    """Email hoặc mật khẩu được cung cấp không hợp lệ."""


class InactiveManagerUser(Exception):
    """Tài khoản quản trị không được phép đăng nhập vì không hoạt động."""
