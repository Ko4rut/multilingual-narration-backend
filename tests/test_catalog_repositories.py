from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.domains.catalog.repositories import (
    LanguageRepository,
    PoiCategoryRepository,
    RegionRepository,
)
from app.domains.catalog.models import LanguageStatus, Region


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


def test_region_get_choices_orders_by_name_then_id():
    session = MagicMock(spec=Session)
    expected = [MagicMock()]
    session.scalars.return_value = expected

    result = RegionRepository(session).get_choices()

    assert result == expected
    statement = session.scalars.call_args.args[0]
    assert "ORDER BY region.region_name, region.id" in str(statement)


def test_region_get_by_id_uses_primary_key_lookup():
    session = MagicMock(spec=Session)
    expected = MagicMock()
    session.get.return_value = expected

    result = RegionRepository(session).get_by_id("region-1")

    assert result is expected
    session.get.assert_called_once_with(Region, "region-1")


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


def test_category_get_choices_orders_by_name_then_id():
    session = MagicMock(spec=Session)
    expected = [MagicMock()]
    session.scalars.return_value = expected

    result = PoiCategoryRepository(session).get_choices()

    assert result == expected
    statement = session.scalars.call_args.args[0]
    assert "ORDER BY poi_category.category_name, poi_category.id" in str(statement)


def test_category_get_existing_ids_returns_only_database_matches():
    session = MagicMock(spec=Session)
    session.scalars.return_value = ["cat-1"]

    result = PoiCategoryRepository(session).get_existing_ids(["cat-1", "cat-missing"])

    assert result == {"cat-1"}
    statement = session.scalars.call_args.args[0]
    assert "poi_category.id IN" in str(statement)


def test_category_get_existing_ids_skips_query_for_empty_input():
    session = MagicMock(spec=Session)

    assert PoiCategoryRepository(session).get_existing_ids([]) == set()
    session.scalars.assert_not_called()


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
