class InvalidAccessToken(Exception):
    """JWT không hợp lệ, hết hạn hoặc không khớp trạng thái Identity hiện tại."""
