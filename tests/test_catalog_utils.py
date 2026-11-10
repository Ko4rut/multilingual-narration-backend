from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

from app.domains.catalog.utils import get_constraint_name


def test_get_constraint_name_reads_postgresql_diagnostic() -> None:
    original = SimpleNamespace(
        diag=SimpleNamespace(constraint_name="language_language_code_key")
    )
    error = IntegrityError(None, None, original)

    assert get_constraint_name(error) == "language_language_code_key"


def test_get_constraint_name_returns_none_without_diagnostic() -> None:
    error = IntegrityError(None, None, Exception("database error"))

    assert get_constraint_name(error) is None
