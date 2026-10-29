from datetime import datetime, timezone
import re
from secrets import token_hex


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(email: str) -> str:
    """Chuẩn hóa email về chữ thường và kiểm tra định dạng cơ bản."""
    normalized_email = email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized_email):
        raise ValueError("email must be a valid email address")
    return normalized_email


def required_text(value: str, field_name: str) -> str:
    """Loại khoảng trắng bao quanh và từ chối chuỗi rỗng."""
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} must not be empty")
    return normalized_value


def generate_dated_identifier(prefix: str, created_at: datetime) -> str:
    """Generate identifiers in the documented prefix-ddmmyy-xxxxxxxx format."""
    return f"{prefix}-{created_at:%d%m%y}-{token_hex(4)}"


def generate_reference_identifier(prefix: str) -> str:
    """Generate stable-format reference IDs such as ``role-xxxxxxxx``."""
    return f"{prefix}-{token_hex(4)}"
