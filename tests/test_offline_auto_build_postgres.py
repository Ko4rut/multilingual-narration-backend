"""Real PostgreSQL end-to-end verification of automatic package lifecycle."""

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from secrets import token_hex

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.domains.catalog.models.language import Language, LanguageStatus
from app.domains.catalog.models.region import Region
from app.domains.identity.models.manager_user import ManagerUserModel, ManagerUserStatus
from app.domains.identity.models.role import RoleModel
from app.domains.offline.models.build_request import OfflineBuildRequest
from app.domains.offline.models.offline_package import OfflinePackage, OfflinePackageStatus
from app.domains.offline.models.offline_package_item import OfflinePackageItem
from app.domains.offline.models.package_release import OfflinePackageRelease
from app.domains.offline.services.build import OfflinePackageBuildService
from app.domains.offline.services.events import enqueue_offline_build
from app.domains.offline.storage.manifest import FileSystemManifestStorage
from app.domains.poi.models.content_audio import ContentAudio
from app.domains.poi.models.poi_content import PoiContent
from app.domains.poi.models.point_of_interest import PointOfInterest
from scripts.offline_worker import process_next


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Requires isolated PostgreSQL")
def test_worker_creates_rebuilds_and_preserves_immutable_versions(tmp_path):
    from types import SimpleNamespace

    engine = create_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    stamp = token_hex(5)
    region_id, language_id = f"region-auto-{stamp}", f"lang-auto-{stamp}"
    role_id, user_id = f"role-auto-{stamp}", f"user-auto-{stamp}"
    poi_id, content_id, audio_id = (
        f"poi-auto-{stamp}", f"cont-auto-{stamp}", f"audio-auto-{stamp}",
    )
    now = datetime.now(timezone.utc)
    sound = b"local-test-audio-content"
    picture = b"\x89PNG\r\n\x1a\n" + b"local-test-image-content"
    audio_sha, image_sha = sha256(sound).hexdigest(), sha256(picture).hexdigest()
    (tmp_path / (audio_sha + ".mp3")).write_bytes(sound)
    (tmp_path / (image_sha + ".png")).write_bytes(picture)
    settings = SimpleNamespace(
        tts_audio_dir=tmp_path,
        poi_image_dir=tmp_path,
        tts_audio_public_base_url="http://localhost:8000/api/v1/assets/audio",
        poi_image_public_base_url="http://localhost:8000/api/v1/assets/images/pois",
        offline_manifest_public_base_url="http://localhost:8000/api/v1/offline/manifests",
    )
    store = FileSystemManifestStorage(tmp_path / "manifests")
    builder = OfflinePackageBuildService(factory, store, settings)
    package_id = None
    try:
        with factory() as session, session.begin():
            session.add_all([
                RoleModel(
                    id=role_id, name=f"Auto build {stamp}", description=None,
                    created_by=None, last_updated_by=None,
                    created_at=now, last_updated_at=now,
                ),
                Region(
                    id=region_id, region_name=f"Auto region {stamp}",
                    region_code=f"T{stamp.upper()}",
                ),
                Language(
                    id=language_id, language_name=f"Auto language {stamp}",
                    language_code="qza", language_status=LanguageStatus.SUPPORTED,
                ),
            ])
            session.flush()
            session.add(ManagerUserModel(
                id=user_id, role_id=role_id, email=f"autobuild-{stamp}@test.invalid",
                password_hash="test-hash", full_name="Auto Builder",
                user_status=ManagerUserStatus.ACTIVE,
                created_at=now, last_updated_at=now, last_login_at=None,
            ))
            session.flush()
            session.add(PointOfInterest(
                id=poi_id, region_id=region_id, poi_name="First title",
                poi_location=f"POI location {stamp}",
                poi_image_url=settings.poi_image_public_base_url + "/" + image_sha + ".png",
                image_checksum_sha256=image_sha, poi_qr_code=f"qr-auto-{stamp}",
                poi_status="ACTIVE", latitude=Decimal("16.000001"),
                longitude=Decimal("108.000001"), trigger_radius_meter=Decimal("50"),
                created_by=user_id, last_updated_by=user_id,
                created_at=now, last_updated_at=now,
            ))
            session.flush()
            session.add(PoiContent(
                id=content_id, poi_id=poi_id, language_id=language_id,
                narration_title="Narration", narration_script="Hello visitor",
                content_version=1, content_status="PUBLISHED", created_by=user_id,
                approved_by=user_id, published_by=user_id,
                created_at=now, approved_at=now, published_at=now,
            ))
            session.flush()
            session.add(ContentAudio(
                id=audio_id, poi_content_id=content_id,
                audio_url=settings.tts_audio_public_base_url + "/" + audio_sha + ".mp3",
                audio_size=len(sound), audio_source_type="TTS",
                audio_duration_sec=10, audio_mime_type="audio/mpeg",
                audio_checksum_sha256=audio_sha, created_at=now, last_updated_at=now,
            ))
            enqueue_offline_build(session, region_id=region_id)

        assert process_next(factory, builder)
        with factory() as session:
            package = session.scalar(
                select(OfflinePackage).where(OfflinePackage.region_id == region_id)
            )
            assert package is not None
            package_id = package.id
            assert package.package_status is OfflinePackageStatus.PUBLISHED
            assert package.package_version == 1
            first_sha = package.package_checksum_sha256
            assert session.get(OfflinePackageRelease, (package.id, 1)) is not None
            jobs = session.scalars(
                select(OfflineBuildRequest).where(OfflineBuildRequest.region_id == region_id)
            ).all()
            assert all(job.status == "SUCCEEDED" for job in jobs)

        with factory() as session, session.begin():
            poi = session.get(PointOfInterest, poi_id)
            poi.poi_name = "Updated title"
            poi.last_updated_at = datetime.now(timezone.utc)
            enqueue_offline_build(session, region_id=region_id)

        assert process_next(factory, builder)
        with factory() as session:
            package = session.get(OfflinePackage, package_id)
            assert package.package_version == 2
            assert package.package_status is OfflinePackageStatus.PUBLISHED
            second_sha = package.package_checksum_sha256
            old = store.read_published(package_id, 1, first_sha)
            new = store.read_published(package_id, 2, second_sha)
            assert json.loads(old)["items"][0]["poi_name"] == "First title"
            assert json.loads(new)["items"][0]["poi_name"] == "Updated title"
            assert session.get(OfflinePackageRelease, (package_id, 1))
            assert session.get(OfflinePackageRelease, (package_id, 2))

        with factory() as session, session.begin():
            enqueue_offline_build(session, region_id=region_id)
        assert process_next(factory, builder)
        with factory() as session:
            assert session.get(OfflinePackage, package_id).package_version == 2

    finally:
        with factory() as session, session.begin():
            session.execute(delete(OfflineBuildRequest).where(
                OfflineBuildRequest.region_id == region_id
            ))
            session.execute(delete(OfflinePackageRelease).where(
                OfflinePackageRelease.package_id == package_id
            )) if package_id else None
            session.execute(delete(OfflinePackageItem).where(
                OfflinePackageItem.package_id == package_id
            )) if package_id else None
            session.execute(delete(OfflinePackage).where(
                OfflinePackage.region_id == region_id
            ))
            session.execute(delete(ContentAudio).where(ContentAudio.id == audio_id))
            session.execute(delete(PoiContent).where(PoiContent.id == content_id))
            session.execute(delete(PointOfInterest).where(PointOfInterest.id == poi_id))
            session.execute(delete(ManagerUserModel).where(ManagerUserModel.id == user_id))
            session.execute(delete(RoleModel).where(RoleModel.id == role_id))
            session.execute(delete(Language).where(Language.id == language_id))
            session.execute(delete(Region).where(Region.id == region_id))
        engine.dispose()
