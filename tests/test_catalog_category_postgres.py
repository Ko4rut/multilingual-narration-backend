"""Opt-in integration against an isolated, migrated PostgreSQL test database."""

import os
from secrets import token_hex

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.domains.catalog.exceptions import (
    PoiCategoryAlreadyExists,
    PoiCategoryInUse,
    PoiCategoryNotFound,
)
from app.domains.catalog.repositories import PoiCategoryRepository
from app.domains.catalog.services import CatalogService


pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL must point to an isolated migrated PostgreSQL database",
)


def make_service(session: Session) -> CatalogService:
    return CatalogService(
        session=session,
        category_repository=PoiCategoryRepository(session),
        language_repository=None,
        region_repository=None,
    )


def test_category_crud_and_constraints_in_isolated_postgres():
    database_url = os.environ["TEST_DATABASE_URL"]
    engine = create_engine(database_url)
    suffix = token_hex(4)
    code = "ci-category-" + suffix
    name = "CI Category " + suffix
    category_id = None
    try:
        inspector = inspect(engine)
        foreign_keys = inspector.get_foreign_keys("poi_category_mapping")
        mapping_foreign_key = next(
            fk for fk in foreign_keys
            if fk["constrained_columns"] == ["poi_category_id"]
        )
        assert mapping_foreign_key["options"].get("ondelete") == "RESTRICT"

        with Session(engine) as session:
            created = make_service(session).create_category(
                category_name=name, category_code=code,
            )
            category_id = created.id
        assert category_id is not None

        with Session(engine) as session:
            with pytest.raises(PoiCategoryAlreadyExists):
                make_service(session).create_category(
                    category_name=name, category_code=code + "-other",
                )

        with Session(engine) as session:
            updated = make_service(session).update_category(
                category_id, category_name="Updated " + name,
            )
            assert updated.category_code == code

        # Data must be persisted and checked without fake repository/session.
        with engine.connect() as connection:
            record = connection.execute(
                text(
                    "SELECT category_name, category_code FROM poi_category "
                    "WHERE id = :category_id"
                ),
                {"category_id": category_id},
            ).one()
        assert record.category_name == "Updated " + name
        assert record.category_code == code

        with Session(engine) as session:
            make_service(session).delete_category(category_id)
        category_id = None
    finally:
        if category_id is not None:
            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM poi_category WHERE id = :category_id"),
                    {"category_id": category_id},
                )
        engine.dispose()
