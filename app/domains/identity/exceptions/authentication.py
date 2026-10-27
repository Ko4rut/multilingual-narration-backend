class InvalidCredentials(Exception):
    """Email hoặc mật khẩu được cung cấp không hợp lệ."""


class InvalidAccessToken(Exception):
    """Access Token không thể dùng để xác thực request."""
