"""Unit-level coverage for offline publication, event queuing and asset checks."""

from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.domains.catalog.models.language import LanguageStatus
from app.domains.offline.models.build_request import OfflineBuildRequest
from app.domains.offline.models.offline_package import OfflinePackageStatus
from app.domains.offline.models.package_release import OfflinePackageRelease
from app.domains.offline.services.assets import OfflineAssetVerifier
from app.domains.offline.services.events import enqueue_offline_build
from app.domains.offline.services.offline import OfflinePackageService
from app.domains.offline.storage.manifest import (
    FileSystemManifestStorage, ManifestStorageCorrupt, ManifestStorageNotFound,
)
from app.domains.offline.repositories.offline_package_item import OfflineCandidate
from app.domains.offline.utils.manifest import manifest_bytes
from app.domains.offline.utils.manifest_diff import AssetDownload


def manifest(*, version=1, title="Title"):
    import json
    return (json.dumps({
        "schema_version": 1, "package_key": "region:DN|lang:ja",
        "package_version": version, "region_code": "DN",
        "language_code": "ja", "category_code": None,
        "items": [], "generated_at": "2026-11-24T00:00:00Z",
        "title_for_test": title,
    }, sort_keys=True) + "\n").encode()


def test_published_manifests_are_immutable_and_content_addressed(tmp_path):
    storage = FileSystemManifestStorage(tmp_path)
    first = storage.save_published("pack-1", 1, manifest())
    second = storage.save_published("pack-1", 1, manifest(title="new"))
    assert first.path != second.path
    assert storage.read_published("pack-1", 1, first.sha256) == manifest()
    assert storage.read_published("pack-1", 1, second.sha256) == manifest(title="new")
    first.path.write_bytes(b"corrupt")
    with pytest.raises(ManifestStorageCorrupt):
        storage.read_published("pack-1", 1, first.sha256)
    with pytest.raises(ManifestStorageNotFound):
        storage.read_published("pack-1", 2, "a" * 64)
    with pytest.raises(ValueError):
        storage.published_path("../escape", 1, "a" * 64)


def test_offline_events_share_source_session_and_dedupe_in_transaction():
    class SessionStub:
        def __init__(self):
            self.new = []

        def add(self, item):
            self.new.append(item)

    session = SessionStub()
    enqueue_offline_build(session, region_id="region-1")
    enqueue_offline_build(session, region_id="region-1")
    enqueue_offline_build(session, region_id="region-1", language_id="lang-ja")
    assert len(session.new) == 2
    assert isinstance(session.new[0], OfflineBuildRequest)
    assert session.new[0].status == "PENDING"
    assert session.new[1].language_id == "lang-ja"


def test_managed_audio_checksum_and_size_verified_from_actual_file(tmp_path):
    content = b"audio demo bytes"
    digest = sha256(content).hexdigest()
    (tmp_path / (digest + ".mp3")).write_bytes(content)
    config = SimpleNamespace(
        tts_audio_dir=tmp_path,
        tts_audio_public_base_url="http://localhost:8000/api/v1/assets/audio",
        poi_image_dir=tmp_path,
        poi_image_public_base_url="http://localhost:8000/api/v1/assets/images/pois",
    )
    verifier = OfflineAssetVerifier(config)
    url = config.tts_audio_public_base_url + "/" + digest + ".mp3"
    assert verifier.verify(AssetDownload("audio", url, digest, len(content)))
    assert not verifier.verify(AssetDownload("audio", url, "a" * 64, len(content)))
    assert not verifier.verify(AssetDownload("audio", url, digest, len(content) + 1))


def test_initial_publish_promotes_building_and_records_release():
    now = datetime(2026, 11, 24, tzinfo=timezone.utc)
    poi = SimpleNamespace(
        id="poi-1", region_id="region-1", poi_name="POI", poi_location="Da Nang",
        latitude=Decimal("16.0"), longitude=Decimal("108.0"),
        trigger_radius_meter=Decimal("50"),
        poi_image_url="https://example.com/img.jpg", image_checksum_sha256="a" * 64,
    )
    content = SimpleNamespace(
        id="cont-1", poi_id="poi-1", language_id="lang-1", content_version=1,
        narration_title="Title", narration_script="Script",
    )
    audio = SimpleNamespace(
        id="audio-1", poi_content_id="cont-1", audio_url="https://example.com/a.mp3",
        audio_size=5, audio_duration_sec=1,
        audio_mime_type="audio/mpeg", audio_checksum_sha256="b" * 64,
    )
    candidate = OfflineCandidate(poi=poi, content=content, audio=audio)
    raw = manifest_bytes(
        package_key="region:DN|lang:ja", package_version=1,
        region_code="DN", language_code="ja", category_code=None,
        candidates=[candidate], generated_at=now,
    )
    package = SimpleNamespace(
        id="pack-1", region_id="region-1", language_id="lang-1", category_id=None,
        package_key="region:DN|lang:ja", schema_version=1, package_version=1,
        package_status=OfflinePackageStatus.BUILDING,
    )
    session = MagicMock(spec=Session)
    session.get.side_effect = lambda model, pk: {
        "Region": SimpleNamespace(region_code="DN"),
        "Language": SimpleNamespace(language_code="ja", language_status=LanguageStatus.SUPPORTED),
    }[model.__name__]
    packages, items = MagicMock(), MagicMock()
    packages.get_by_id.return_value = package
    items.select_candidates.return_value = [candidate]
    service = OfflinePackageService(session, packages, items)
    result = service.publish_initial_package(
        package_id="pack-1", manifest=raw,
        manifest_url="https://cdn.example.com/manifests/v1/a.json",
        verify_manifest=lambda _u, _b: True, verify_asset=lambda _a: True,
    )
    assert result.package_status is OfflinePackageStatus.PUBLISHED
    assert result.package_checksum_sha256 == sha256(raw).hexdigest()
    release = session.add.call_args.args[0]
    assert isinstance(release, OfflinePackageRelease)
    assert release.package_id == "pack-1" and release.package_version == 1
    items.sync_membership.assert_called_once()
