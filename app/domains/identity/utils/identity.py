from datetime import datetime, timezone
from secrets import token_hex


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_dated_identifier(prefix: str, created_at: datetime) -> str:
    """Generate identifiers in the documented prefix-ddmmyy-xxxxxxxx format."""

    return f"{prefix}-{created_at:%d%m%y}-{token_hex(4)}"
