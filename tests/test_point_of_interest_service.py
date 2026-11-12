import re
from contextlib import nullcontext
from datetime import datetime, timezone
from decimal import Decimal

from app.domains.poi.models.point_of_interest import PointOfInterest
from app.domains.poi.schemas.point_of_interest import PoiCreate, PoiUpdate
from app.domains.poi.services.point_of_interest import (
    PointOfInterestService,
)


class SessionStub:
    def __init__(self) -> None:
        self.flush_count = 0

    def begin(self):
        return nullcontext()

    def flush(self) -> None:
        self.flush_count += 1


class PoiRepositoryStub:
    def __init__(self, record: PointOfInterest | None = None) -> None:
        self.record = record
        self.added = None

    def get_by_id(self, poi_id: str, *, for_update: bool = False):
        return self.record

    def add(self, poi: PointOfInterest) -> None:
        self.record = poi
        self.added = poi


class MappingRepositoryStub:
    def __init__(self) -> None:
        self.category_ids: list[str] = []
        self.replacements: list[tuple[str, list[str]]] = []

    def get_category_ids_by_poi_ids(self, poi_ids: list[str]):
        return {poi_id: list(self.category_ids) for poi_id in poi_ids}

    def replace_for_poi(self, poi_id: str, category_ids: list[str]) -> None:
        self.category_ids = list(category_ids)
        self.replacements.append((poi_id, list(category_ids)))


class ContentRepositoryStub:
    def get_published_english_contents(self, poi_ids: list[str]):
        return {}


class AudioRepositoryStub:
    def get_content_ids_with_valid_audio(self, content_ids: list[str]):
        return set()


class CategoryRepositoryStub:
    def get_choices(self):
        return []

    def get_existing_ids(self, category_ids: list[str]):
        return set(category_ids)


class RegionRepositoryStub:
    def get_choices(self):
        return []

    def get_by_id(self, region_id: str):
        return object()


class ImageChecksumStub:
    checksum = "a" * 64

    def __init__(self) -> None:
        self.urls: list[str] = []

    def calculate(self, url: str) -> str:
        self.urls.append(url)
        return self.checksum


def make_poi() -> PointOfInterest:
    now = datetime.now(timezone.utc)
    return PointOfInterest(
        id="poi-010126-12345678",
        region_id="region-1",
        poi_image_url="https://assets.example/poi.webp",
        image_checksum_sha256=None,
        poi_qr_code="museum-qr",
        poi_name="Museum",
        poi_location="Museum address",
        poi_status="INACTIVE",
        latitude=Decimal("10.000000"),
        longitude=Decimal("106.000000"),
        trigger_radius_meter=Decimal("50.00"),
        created_by="user-1",
        last_updated_by="user-1",
        created_at=now,
        last_updated_at=now,
    )


def build_service(record: PointOfInterest | None = None):
    session = SessionStub()
    repository = PoiRepositoryStub(record)
    mappings = MappingRepositoryStub()
    contents = ContentRepositoryStub()
    image_checksums = ImageChecksumStub()
    service = PointOfInterestService(
        session=session,
        repository=repository,
        mappings=mappings,
        contents=contents,
        audios=AudioRepositoryStub(),
        categories=CategoryRepositoryStub(),
        regions=RegionRepositoryStub(),
        image_checksums=image_checksums,
    )
    return service, session, repository, mappings, contents, image_checksums


def test_create_poi_sets_inactive_status_actor_and_categories() -> None:
    service, session, repository, mappings, _, image_checksums = build_service()
    payload = PoiCreate(
        region_id="region-1",
        poi_name="Museum",
        poi_location="Museum address",
        poi_image_url="https://assets.example/poi.webp",
        latitude=Decimal("10.000000"),
        longitude=Decimal("106.000000"),
        trigger_radius_meter=Decimal("50.00"),
        category_ids=["cat-1"],
    )

    result = service.create_poi(payload, actor_id="user-1")

    assert repository.added is not None
    assert re.fullmatch(r"poi-\d{6}-[0-9a-f]{8}", repository.added.id)
    assert repository.added.poi_qr_code == f"mnr://pois/{repository.added.id}"
    assert repository.added.poi_status == "INACTIVE"
    assert repository.added.created_by == "user-1"
    assert repository.added.image_checksum_sha256 == "a" * 64
    assert image_checksums.urls == ["https://assets.example/poi.webp"]
    assert result.category_ids == ["cat-1"]
    assert result.qr_code_url == f"/api/v1/admin/pois/{repository.added.id}/qr-code"
    assert mappings.replacements == [(repository.added.id, ["cat-1"])]
    assert session.flush_count == 2


def test_update_poi_changes_fields_and_audit_metadata() -> None:
    poi = make_poi()
    service, _, _, _, _, image_checksums = build_service(poi)

    result = service.update_poi(
        poi.id,
        PoiUpdate(poi_name="Updated museum"),
        actor_id="user-2",
    )

    assert poi.poi_name == "Updated museum"
    assert poi.last_updated_by == "user-2"
    assert result.poi_name == "Updated museum"
    assert image_checksums.urls == []


def test_update_poi_recalculates_checksum_when_image_url_is_sent() -> None:
    poi = make_poi()
    service, _, _, _, _, image_checksums = build_service(poi)

    service.update_poi(
        poi.id,
        PoiUpdate(poi_image_url="https://assets.example/new-poi.webp"),
        actor_id="user-2",
    )

    assert image_checksums.urls == ["https://assets.example/new-poi.webp"]
    assert poi.image_checksum_sha256 == "a" * 64
