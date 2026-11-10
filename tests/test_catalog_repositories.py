from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.domains.catalog.repositories import (
    LanguageRepository,
    PoiCategoryRepository,
    RegionRepository,
)
from app.domains.catalog.models import LanguageStatus


def test_region_get_all_orders_by_id_without_pagination():
    session = MagicMock(spec=Session)
    expected = [MagicMock()]
    session.scalars.return_value = expected

    result = RegionRepository(session).get_all()

    assert result == expected
    statement = session.scalars.call_args.args[0]
    assert "ORDER BY region.id" in str(statement)
    assert statement._limit_clause is None
    assert statement._offset_clause is None


def test_category_get_all_orders_by_id_without_pagination():
    session = MagicMock(spec=Session)
    expected = [MagicMock()]
    session.scalars.return_value = expected

    result = PoiCategoryRepository(session).get_all()

    assert result == expected
    statement = session.scalars.call_args.args[0]
    assert "ORDER BY poi_category.id" in str(statement)
    assert statement._limit_clause is None
    assert statement._offset_clause is None


def test_language_get_supported_filters_status_and_orders_by_id():
    session = MagicMock(spec=Session)
    expected = [MagicMock()]
    session.scalars.return_value = expected

    result = LanguageRepository(session).get_supported()

    assert result == expected
    statement = session.scalars.call_args.args[0]
    rendered = str(statement)
    assert "language.language_status" in rendered
    assert "ORDER BY language.id" in rendered
    assert statement.compile().params == {"language_status_1": LanguageStatus.SUPPORTED}
    assert statement._limit_clause is None
    assert statement._offset_clause is None


def test_language_get_all_orders_by_id_without_pagination():
    session = MagicMock(spec=Session)
    expected = [MagicMock()]
    session.scalars.return_value = expected

    result = LanguageRepository(session).get_all()

    assert result == expected
    statement = session.scalars.call_args.args[0]
    assert "ORDER BY language.id" in str(statement)
    assert statement._limit_clause is None
    assert statement._offset_clause is None
