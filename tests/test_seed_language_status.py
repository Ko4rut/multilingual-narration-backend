"""Tests for explicit legacy Language status reconciliation before Alembic 0005."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.domains.catalog.models.language import LanguageStatus
from scripts.seed import reconcile_legacy_language_statuses, seed_catalog


def make_language_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE language (language_code TEXT, language_status TEXT)")
        )
    return engine


def test_reconciliation_on_empty_docker_database_is_noop():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with Session(engine) as session:
        assert reconcile_legacy_language_statuses(session) == 0


def test_reconciliation_normalizes_known_legacy_values_and_is_idempotent():
    engine = make_language_session()
    with Session(engine) as session, session.begin():
        session.execute(
            text(
                "INSERT INTO language(language_code, language_status) "
                "VALUES ('vi', 'active'), ('en', ' supported '), "
                "('fr', 'UNSUPPORTED'), ('ja', ' unsupported ')"
            )
        )
        assert reconcile_legacy_language_statuses(session) == 3
        assert reconcile_legacy_language_statuses(session) == 0

    with Session(engine) as session:
        actual = dict(session.execute(text(
            "SELECT language_code, language_status FROM language"
        )).all())
    assert actual == {
        "vi": "SUPPORTED",
        "en": "SUPPORTED",
        "fr": "UNSUPPORTED",
        "ja": "UNSUPPORTED",
    }


def test_reconciliation_rejects_unknown_status_without_writes():
    engine = make_language_session()
    with Session(engine) as session, session.begin():
        session.execute(text(
            "INSERT INTO language(language_code, language_status) "
            "VALUES ('vi', 'active'), ('en', 'INACTIVE')"
        ))
        with pytest.raises(ValueError, match="Unknown language_status"):
            reconcile_legacy_language_statuses(session)
        actual = dict(session.execute(text(
            "SELECT language_code, language_status FROM language"
        )).all())
        assert actual == {"vi": "active", "en": "INACTIVE"}


def test_seed_catalog_uses_canonical_enum():
    # Verifies the seed source uses typed values; no database or external
    # services are needed for this test.
    from inspect import getsource

    source = getsource(seed_catalog)
    assert "LanguageStatus.SUPPORTED" in source
    assert LanguageStatus.SUPPORTED.value == "SUPPORTED"
