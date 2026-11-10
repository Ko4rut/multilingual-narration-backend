from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.domains.poi.repositories.poi_category_mapping import (
    PoiCategoryMappingRepository,
)


def test_get_category_ids_by_poi_ids_groups_rows_without_n_plus_one() -> None:
    session = MagicMock(spec=Session)
    session.execute.return_value = [
        ("poi-1", "cat-1"),
        ("poi-1", "cat-2"),
        ("poi-2", "cat-2"),
    ]

    result = PoiCategoryMappingRepository(session).get_category_ids_by_poi_ids(
        ["poi-1", "poi-2", "poi-3"]
    )

    assert result == {
        "poi-1": ["cat-1", "cat-2"],
        "poi-2": ["cat-2"],
        "poi-3": [],
    }
    session.execute.assert_called_once()


def test_get_category_ids_by_poi_ids_skips_query_for_empty_input() -> None:
    session = MagicMock(spec=Session)

    result = PoiCategoryMappingRepository(session).get_category_ids_by_poi_ids([])

    assert result == {}
    session.execute.assert_not_called()


def test_replace_for_poi_deletes_old_rows_and_adds_new_rows() -> None:
    session = MagicMock(spec=Session)

    PoiCategoryMappingRepository(session).replace_for_poi(
        "poi-1",
        ["cat-1", "cat-2"],
    )

    session.execute.assert_called_once()
    delete_statement = str(session.execute.call_args.args[0])
    assert "DELETE FROM poi_category_mapping" in delete_statement
    assert "poi_category_mapping.poi_id" in delete_statement
    mappings = session.add_all.call_args.args[0]
    assert [
        (mapping.poi_id, mapping.poi_category_id) for mapping in mappings
    ] == [
        ("poi-1", "cat-1"),
        ("poi-1", "cat-2"),
    ]
