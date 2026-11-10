from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.domains.poi.repositories.content_audio import ContentAudioRepository
from app.domains.poi.repositories.poi_content import PoiContentRepository
from app.domains.poi.repositories.point_of_interest import PoiRepository


def test_get_all_supports_status_filter_and_stable_pagination() -> None:
    session = MagicMock(spec=Session)
    expected = [MagicMock()]
    session.scalars.return_value = expected

    result = PoiRepository(session).get_all(
        offset=20,
        limit=10,
        poi_status="ACTIVE",
        sort_by="id",
    )

    assert result == expected
    statement = session.scalars.call_args.args[0]
    rendered = str(statement)
    assert "upper(point_of_interest.poi_status)" in rendered
    assert "ACTIVE" in statement.compile().params.values()
    assert "ORDER BY point_of_interest.id" in rendered
    assert statement._offset_clause is not None
    assert statement._limit_clause is not None


def test_get_all_orders_pois_for_content_options() -> None:
    session = MagicMock(spec=Session)
    expected = [MagicMock()]
    session.scalars.return_value = expected

    result = PoiRepository(session).get_all()

    assert result == expected
    statement = session.scalars.call_args.args[0]
    rendered = str(statement)
    assert "ORDER BY point_of_interest.poi_name, point_of_interest.id" in rendered


def test_get_count_uses_same_status_filter_without_treating_other_values_as_inactive() -> None:
    session = MagicMock(spec=Session)
    session.scalar.return_value = 0

    total = PoiRepository(session).get_count(
        search=None,
        poi_status="INACTIVE",
        region_id=None,
        category_id=None,
    )

    assert total == 0
    count_statement = session.scalar.call_args.args[0]
    rendered = str(count_statement)
    assert "upper(point_of_interest.poi_status)" in rendered
    assert "!=" not in rendered
    assert "INACTIVE" in count_statement.compile().params.values()


def test_get_by_id_can_limit_result_to_active_poi() -> None:
    session = MagicMock(spec=Session)
    expected = MagicMock()
    session.scalar.return_value = expected

    result = PoiRepository(session).get_by_id("poi-1", active_only=True)

    assert result is expected
    statement = session.scalar.call_args.args[0]
    rendered = str(statement)
    assert "point_of_interest.id" in rendered
    assert "point_of_interest.poi_status" in rendered


def test_content_list_and_count_share_filters() -> None:
    session = MagicMock(spec=Session)
    session.scalars.return_value = []
    session.scalar.return_value = 4
    repository = PoiContentRepository(session)
    filters = {
        "poi_id": "poi-1",
        "language_id": None,
        "content_status": "PUBLISHED",
        "search": "museum",
    }

    assert repository.get_all(offset=0, limit=20, **filters) == []
    assert repository.get_count(**filters) == 4

    list_sql = str(session.scalars.call_args.args[0])
    count_sql = str(session.scalar.call_args.args[0])
    for expected in ("poi_content.poi_id", "poi_content.content_status", "narration_title"):
        assert expected in list_sql
        assert expected in count_sql


def test_audio_list_and_count_share_joined_filters() -> None:
    session = MagicMock(spec=Session)
    session.scalars.return_value = []
    session.scalar.return_value = 2
    repository = ContentAudioRepository(session)
    filters = {
        "poi_id": "poi-1",
        "language_id": "lang-1",
        "poi_content_id": None,
        "audio_source_type": "TTS",
        "search": "museum",
    }

    assert repository.get_all(offset=0, limit=20, **filters) == []
    assert repository.get_count(**filters) == 2

    list_sql = str(session.scalars.call_args.args[0])
    count_sql = str(session.scalar.call_args.args[0])
    for expected in ("JOIN poi_content", "poi_content.poi_id", "audio_source_type"):
        assert expected in list_sql
        assert expected in count_sql
