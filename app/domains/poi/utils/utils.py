"""Các hàm tiện ích dùng chung trong domain POI."""

from datetime import datetime
from secrets import token_hex

from sqlalchemy.exc import IntegrityError


def generate_dated_identifier(prefix: str, created_at: datetime) -> str:
    """Sinh ID theo định dạng ``prefix-ddmmyy-xxxxxxxx`` trong tài liệu."""
    return f"{prefix}-{created_at:%d%m%y}-{token_hex(4)}"


def escape_like_value(value: str) -> str:
    """Escape ký tự đặc biệt trước khi dùng giá trị trong biểu thức LIKE."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_constraint_name(exc: IntegrityError) -> str | None:
    """Lấy tên constraint PostgreSQL từ diagnostic của driver, nếu có."""
    diagnostic = getattr(exc.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None)
