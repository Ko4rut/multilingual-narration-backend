"""Change detection tests: no extra hashes, DB migrations, or external storage."""

import json
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.domains.catalog.models.language import LanguageStatus
from app.domains.offline.models.offline_package import OfflinePackageStatus
from app.domains.offline.repositories.offline_package_item import OfflineCandidate
from app.domains.offline.services.offline import (
    OfflinePackagePreparationError, OfflinePackageService,
)
from app.domains.offline.utils.manifest import manifest_bytes
from app.domains.offline.utils.manifest_diff import (
    InvalidOfflineManifest, compare_manifests, load_manifest,
    validate_published_manifest,
)
from tests.test_offline_repository import NOW, sample_candidate


def manifest(candidates, *, version=1):
    return manifest_bytes(
        package_key="region:HAN|lang:vi",
        package_version=version, region_code="HAN", language_code="vi",
        category_code=None, candidates=candidates, generated_at=NOW,
    )


def diff(old_candidates, new_candidates):
    old = load_manifest(manifest(old_candidates, version=1))
    new = load_manifest(manifest(new_candidates, version=2))
    return compare_manifests(old, new)


def test_same_snapshot_ignores_generated_time_and_version():
    candidate = sample_candidate()
    baseline = load_manifest(manifest([candidate]))
    proposed = dict(baseline, generated_at="2027-01-01T00:00:00Z", package_version=2)
    changes = compare_manifests(baseline, proposed)
    assert not changes.changed
    assert not changes.assets_to_download


def test_coordinates_or_script_change_updates_only_one_poi_without_audio_download():
    first = sample_candidate(poi_id="poi-1", content_id="cont-1")
    second = sample_candidate(poi_id="poi-2", content_id="cont-2")
    before = load_manifest(manifest([first, second]))
    after = load_manifest(manifest([first, second], version=2))
    after["items"][0]["latitude"] = "21.111111"
    after["items"][0]["narration_script"] = "New narration"
    changes = compare_manifests(before, after)
    assert changes.updated_poi_ids == ("poi-1",)
    assert changes.added_poi_ids == ()
    assert changes.removed_poi_ids == ()
    assert changes.assets_to_download == ()


def test_added_and_removed_pois_and_audio_change():
    first = sample_candidate(poi_id="poi-1", content_id="cont-1")
    second = sample_candidate(poi_id="poi-2", content_id="cont-2")
    old = load_manifest(manifest([first]))
    new = load_manifest(manifest([second], version=2))
    new["items"][0]["audio"]["sha256"] = "d" * 64
    delta = compare_manifests(old, new)
    assert delta.added_poi_ids == ("poi-2",)
    assert delta.removed_poi_ids == ("poi-1",)
    assert delta.updated_poi_ids == ()
    assert {(a.kind, a.sha256) for a in delta.assets_to_download} == {
        ("audio", "d" * 64),
    }


def test_changed_audio_is_downloaded_once_even_if_shared():
    old = load_manifest(manifest([sample_candidate()]))
    new = load_manifest(manifest([sample_candidate()], version=2))
    new["items"][0]["audio"]["sha256"] = "c" * 64
    new["items"][0]["audio"]["url"] = "https://cdn.example.local/v2.mp3"
    changes = compare_manifests(old, new)
    assert changes.updated_poi_ids == ("poi-1",)
    assert len(changes.assets_to_download) == 1
    assert changes.assets_to_download[0].sha256 == "c" * 64


def test_changed_image_url_without_checksum_requires_download():
    old = load_manifest(manifest([sample_candidate()]))
    new = load_manifest(manifest([sample_candidate()], version=2))
    old["items"][0]["image"]["sha256"] = None
    new["items"][0]["image"]["sha256"] = None
    new["items"][0]["image"]["url"] = "https://cdn.example.local/new.jpg"
    delta = compare_manifests(old, new)
    assert [(a.kind, a.url) for a in delta.assets_to_download] == [
        ("image", "https://cdn.example.local/new.jpg"),
    ]


def test_manifest_rejects_malformed_duplicate_and_wrong_checksum():
    raw = manifest([sample_candidate()])
    with pytest.raises(InvalidOfflineManifest, match="SHA-256"):
        validate_published_manifest(
            raw, expected_checksum="0" * 64, expected_key="region:HAN|lang:vi",
            expected_version=1, expected_schema_version=1,
        )
    parsed = validate_published_manifest(
        raw, expected_checksum=sha256(raw).hexdigest(),
        expected_key="region:HAN|lang:vi", expected_version=1,
        expected_schema_version=1,
    )
    assert len(parsed["items"]) == 1
    with pytest.raises(InvalidOfflineManifest, match="metadata"):
        validate_published_manifest(
            raw, expected_checksum=sha256(raw).hexdigest(),
            expected_key="another", expected_version=1,
            expected_schema_version=1,
        )
    malformed = dict(parsed, items=[parsed["items"][0], parsed["items"][0]])
    with pytest.raises(InvalidOfflineManifest, match="Duplicate"):
        load_manifest(json.dumps(malformed).encode())


def plan_service(candidate_list, *, status=OfflinePackageStatus.PUBLISHED):
    session = MagicMock(spec=Session)
    region = SimpleNamespace(id="region-1", region_code="HAN", region_name="Hà Nội")
    language = SimpleNamespace(
        id="lang-vi", language_code="vi", language_name="Tiếng Việt",
        language_status=LanguageStatus.SUPPORTED,
    )
    session.get.side_effect = lambda model, primary_key: {
        "Region": region, "Language": language, "PoiCategory": None,
    }[model.__name__]
    baseline = manifest([sample_candidate()])
    package = SimpleNamespace(
        id="pack-1", region_id=region.id, language_id=language.id,
        category_id=None, package_status=status,
        package_key="region:HAN|lang:vi",
        package_version=1, schema_version=1,
        package_url="https://cdn.example.local/packages/v1.json",
        package_checksum_sha256=sha256(baseline).hexdigest(),
    )
    packages = MagicMock()
    packages.get_by_id.return_value = package
    items = MagicMock()
    items.select_candidates.return_value = candidate_list
    return OfflinePackageService(session, packages, items), packages, items, baseline


def test_plan_rebuild_unchanged_does_not_write_or_bump_version():
    service, packages, items, baseline = plan_service([sample_candidate()])
    planned = service.plan_rebuild(package_id="pack-1", published_manifest=baseline)
    assert not planned.needs_rebuild
    assert planned.manifest is None
    assert planned.expected_version == 1
    packages.add.assert_not_called()
    items.add_all.assert_not_called()


def test_plan_rebuild_remove_last_poi_detected_and_only_stages_manifest():
    service, packages, items, baseline = plan_service([])
    planned = service.plan_rebuild(package_id="pack-1", published_manifest=baseline)
    assert planned.needs_rebuild
    assert planned.changes.removed_poi_ids == ("poi-1",)
    assert json.loads(planned.manifest)["items"] == []
    assert json.loads(planned.manifest)["package_version"] == 2
    packages.add.assert_not_called()
    items.add_all.assert_not_called()


def test_plan_rebuild_refuses_unpublished_or_untrusted_baseline():
    service, packages, items, baseline = plan_service(
        [sample_candidate()], status=OfflinePackageStatus.BUILDING,
    )
    with pytest.raises(OfflinePackagePreparationError, match="published"):
        service.plan_rebuild(package_id="pack-1", published_manifest=baseline)
    items.select_candidates.assert_not_called()
    service, packages, items, baseline = plan_service([sample_candidate()])
    with pytest.raises(InvalidOfflineManifest, match="SHA-256"):
        service.plan_rebuild(package_id="pack-1", published_manifest=baseline + b" ")
    items.select_candidates.assert_not_called()
