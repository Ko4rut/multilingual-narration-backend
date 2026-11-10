"""Group 3 staging repositories and deterministic manifest preparation."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.domains.catalog.models.language import LanguageStatus
from app.domains.offline.models.offline_package import OfflinePackageStatus
from app.domains.offline.models.offline_package_item import OfflinePackageItem
from app.domains.offline.repositories import (
    OfflineCandidate, OfflinePackageItemRepository, OfflinePackageRepository,
)
from app.domains.offline.services.offline import (
    OfflinePackagePreparationError, OfflinePackageService,
)
from app.domains.offline.utils.manifest import manifest_bytes, manifest_sha256


NOW = datetime(2026, 11, 6, 10, 0, tzinfo=timezone.utc)


def sample_candidate(*, poi_id="poi-1", content_id="cont-1"):
    poi = SimpleNamespace(
        id=poi_id, region_id="region-1", poi_name="Hồ Gươm",
        poi_location="Hà Nội", latitude=Decimal("21.030000"),
        longitude=Decimal("105.850000"),
        trigger_radius_meter=Decimal("50.00"),
        poi_image_url="https://cdn.example.local/img.jpg",
        image_checksum_sha256="a" * 64,
    )
    content = SimpleNamespace(
        id=content_id, poi_id=poi.id, language_id="lang-vi",
        content_version=2, narration_title="Hồ Gươm",
        narration_script="Giới thiệu hồ Gươm",
    )
    audio = SimpleNamespace(
        id="audio-" + content_id, poi_content_id=content.id,
        audio_url="https://cdn.example.local/audio.mp3",
        audio_size=2048, audio_duration_sec=15,
        audio_mime_type="audio/mpeg", audio_checksum_sha256="b" * 64,
    )
    return OfflineCandidate(poi=poi, content=content, audio=audio)


def test_candidate_query_requires_active_exact_language_published_and_valid_audio():
    session = MagicMock(spec=Session)
    session.execute.return_value.all.return_value = []
    repository = OfflinePackageItemRepository(session)
    assert repository.select_candidates(
        region_id="region-1", language_id="lang-vi", category_id="cat-1",
    ) == []
    stmt = session.execute.call_args.args[0]
    sql = str(stmt.compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    ))
    assert "point_of_interest.region_id = 'region-1'" in sql
    assert "poi_content.language_id = 'lang-vi'" in sql
    assert "lower(point_of_interest.poi_status)" in sql
    assert "upper(poi_content.content_status)" in sql
    assert "content_audio.audio_size > 0" in sql
    assert "content_audio.audio_duration_sec > 0" in sql
    assert "poi_category_mapping" in sql
    assert "ORDER BY point_of_interest.id, poi_content.id" in sql


def test_package_read_filters_out_building_and_missing_manifest():
    session = MagicMock(spec=Session)
    session.scalars.return_value = []
    repository = OfflinePackageRepository(session)
    assert repository.get_all(
        published_only=True,
        region_id="region-1",
    ) == []
    sql = str(session.scalars.call_args.args[0].compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    ))
    assert "'PUBLISHED'" in sql
    assert "offline_package.package_url IS NOT NULL" in sql
    assert "offline_package.package_checksum_sha256 IS NOT NULL" in sql
    with pytest.raises(ValueError):
        repository.get_all(limit=0)


def test_package_count_uses_the_same_published_filters():
    session = MagicMock(spec=Session)
    session.scalar.return_value = 2
    repository = OfflinePackageRepository(session)

    result = repository.get_count(
        published_only=True,
        region_id="region-1",
    )

    assert result == 2
    sql = str(session.scalar.call_args.args[0].compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    ))
    assert "count" in sql.lower()
    assert "'PUBLISHED'" in sql
    assert "offline_package.region_id = 'region-1'" in sql


def test_manifest_is_deterministic_and_contains_download_metadata():
    c1 = sample_candidate()
    c2 = sample_candidate(poi_id="poi-2", content_id="cont-2")
    common = dict(
        package_key="region:HAN|lang:vi", package_version=1,
        region_code="HAN", language_code="vi", category_code=None,
        generated_at=NOW,
    )
    actual = manifest_bytes(candidates=[c2, c1], **common)
    assert actual == manifest_bytes(candidates=[c1, c2], **common)
    data = json.loads(actual)
    assert data["schema_version"] == 1
    assert data["language_code"] == "vi"
    assert [x["poi_id"] for x in data["items"]] == ["poi-1", "poi-2"]
    assert data["items"][0]["audio"]["sha256"] == "b" * 64
    assert data["items"][0]["audio"]["size"] == 2048
    assert data["items"][0]["image"]["sha256"] == "a" * 64
    assert len(manifest_sha256(actual)) == 64


def test_manifest_rejects_duplicate_or_mismatched_references():
    candidate = sample_candidate()
    common = dict(package_key="region:HAN|lang:vi", package_version=1,
                  region_code="HAN", language_code="vi",
                  category_code=None, generated_at=NOW)
    with pytest.raises(ValueError, match="Duplicate"):
        manifest_bytes(candidates=[candidate, candidate], **common)
    candidate.audio.poi_content_id = "different-content"
    with pytest.raises(ValueError, match="Inconsistent"):
        manifest_bytes(candidates=[candidate], **common)


def make_service(*, candidates=None, language_status=LanguageStatus.SUPPORTED):
    session = MagicMock(spec=Session)
    session.get.side_effect = lambda model, pk: {
        "Region": SimpleNamespace(id="region-1", region_code="HAN",
                                  region_name="Hà Nội"),
        "Language": SimpleNamespace(id="lang-vi", language_code="vi",
                                    language_name="Tiếng Việt",
                                    language_status=language_status),
        "PoiCategory": None,
    }[model.__name__]
    packages = MagicMock()
    packages.get_by_key.return_value = None
    items = MagicMock()
    items.select_candidates.return_value = [sample_candidate()] if candidates is None else candidates
    service = OfflinePackageService(session, packages, items)
    return service, session, packages, items


def test_first_build_stages_package_and_items_but_never_publishes():
    service, session, packages, items = make_service()
    package, raw_manifest = service.prepare_initial_package(
        region_id="region-1", language_id="lang-vi",
    )
    assert package.package_key == "region:HAN|lang:vi"
    assert package.package_status == OfflinePackageStatus.BUILDING
    assert package.package_url is None
    assert package.package_checksum_sha256 is None
    assert package.total_size is None
    assert package.published_at is None
    assert json.loads(raw_manifest)["items"][0]["content_version"] == 2
    staged = items.add_all.call_args.args[0]
    assert len(staged) == 1
    assert isinstance(staged[0], OfflinePackageItem)
    assert staged[0].package_id == package.id
    assert staged[0].audio_id == "audio-cont-1"
    assert staged[0].content_version == 2
    packages.add.assert_called_once_with(package)
    assert session.flush.call_count == 2


def test_existing_package_is_not_rebuilt_or_modified():
    service, _, packages, items = make_service()
    packages.get_by_key.return_value = object()
    with pytest.raises(OfflinePackagePreparationError, match="already exists"):
        service.prepare_initial_package(region_id="region-1", language_id="lang-vi")
    packages.add.assert_not_called()
    items.add_all.assert_not_called()


def test_no_eligible_content_and_unsupported_language_rejected():
    service, _, packages, items = make_service(candidates=[])
    with pytest.raises(OfflinePackagePreparationError, match="No eligible"):
        service.prepare_initial_package(region_id="region-1", language_id="lang-vi")
    packages.add.assert_not_called()
    items.add_all.assert_not_called()

    service, _, packages, items = make_service(
        language_status=LanguageStatus.UNSUPPORTED,
    )
    with pytest.raises(OfflinePackagePreparationError, match="SUPPORTED"):
        service.prepare_initial_package(region_id="region-1", language_id="lang-vi")
    items.select_candidates.assert_not_called()
    packages.add.assert_not_called()


def test_membership_repository_rejects_duplicate_content():
    session = MagicMock(spec=Session)
    item_1 = SimpleNamespace(poi_content_id="same")
    item_2 = SimpleNamespace(poi_content_id="same")
    with pytest.raises(ValueError, match="Duplicate"):
        OfflinePackageItemRepository(session).add_all([item_1, item_2])
    session.add_all.assert_not_called()
