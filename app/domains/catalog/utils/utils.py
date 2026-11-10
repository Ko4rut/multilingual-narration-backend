"""Các hàm tiện ích dùng chung trong domain Catalog."""

from secrets import token_hex

from sqlalchemy.exc import IntegrityError


def generate_catalog_identifier(prefix: str) -> str:
    """Sinh mã định danh theo định dạng ``prefix-xxxxxxxx`` trong tài liệu."""
    return f"{prefix}-{token_hex(4)}"


def normalize_language_code(value: str) -> str:
    """Chuẩn hóa và xác minh mã ISO 639-1 hoặc ISO 639-2."""
    # Chỉ nạp thư viện ISO khi thực sự kiểm tra mã ngôn ngữ để các tiện ích
    # Catalog khác không phụ thuộc vào thư viện này lúc import module.
    from iso639 import is_language

    normalized = value.strip().lower()

    if len(normalized) == 2:
        valid = is_language(normalized, "pt1")
    elif len(normalized) == 3:
        valid = is_language(normalized, ("pt2b", "pt2t"))
    else:
        valid = False

    if not valid:
        raise ValueError(
            "language_code must be a valid ISO 639-1 or ISO 639-2 code"
        )
    return normalized


def normalize_language_name(value: str) -> str:
    """Loại bỏ khoảng trắng thừa và từ chối tên ngôn ngữ rỗng."""
    normalized = value.strip()
    if not normalized:
        raise ValueError("language_name must not be empty")
    return normalized


def get_constraint_name(exc: IntegrityError) -> str | None:
    """Lấy tên constraint do PostgreSQL cung cấp, nếu driver có diagnostic."""
    diagnostic = getattr(exc.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None)
