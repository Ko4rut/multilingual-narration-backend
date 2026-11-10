import re
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

from app.domains.poi.utils import (
    escape_like_value,
    generate_dated_identifier,
    get_constraint_name,
)


def test_generate_dated_identifier_uses_documented_format() -> None:
    created_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

    identifier = generate_dated_identifier("poi", created_at)

    assert re.fullmatch(r"poi-020126-[0-9a-f]{8}", identifier)


def test_escape_like_value_escapes_backslash_and_wildcards() -> None:
    assert escape_like_value(r"a\b%c_d") == r"a\\b\%c\_d"


def test_get_constraint_name_reads_postgresql_diagnostic() -> None:
    original = SimpleNamespace(
        diag=SimpleNamespace(constraint_name="poi_category_mapping_pkey")
    )
    error = IntegrityError(None, None, original)

    assert get_constraint_name(error) == "poi_category_mapping_pkey"


def test_get_constraint_name_returns_none_without_diagnostic() -> None:
    error = IntegrityError(None, None, Exception("database error"))

    assert get_constraint_name(error) is None
