from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFound
from app.domains.catalog.repositories.poi_category import PoiCategoryRepository
from app.domains.catalog.repositories.region import RegionRepository
from app.domains.poi.exceptions import (
    InvalidPoiFilter,
    PoiConflict,
    PoiNotFound,
    PoiReferenceNotFound,
)
from app.domains.poi.providers.image_checksum import RemoteImageChecksumProvider
from app.domains.poi.models.point_of_interest import PointOfInterest
from app.domains.poi.repositories.content_audio import ContentAudioRepository
from app.domains.poi.repositories.poi_category_mapping import PoiCategoryMappingRepository
from app.domains.poi.repositories.poi_content import PoiContentRepository
from app.domains.poi.repositories.point_of_interest import PoiRepository
from app.domains.poi.providers.qr_code import create_poi_qr_payload
from app.domains.poi.schemas.point_of_interest import (
    AdminPoiPage,
    AdminPoiRead,
    PoiCreate,
    PoiFormOptions,
    PoiPage,
    PoiRead,
    PoiUpdate,
)
from app.domains.poi.utils import generate_dated_identifier, get_constraint_name


class PublicPointOfInterestService:
    """Cung cấp các truy vấn POI công khai."""

    def __init__(self, repository: PoiRepository):
        self.repository = repository

    def list_pois(self, *, offset: int, limit: int) -> PoiPage:
        items = self.repository.get_all(
            offset=offset,
            limit=limit,
            poi_status="ACTIVE",
            sort_by="id",
        )
        total = self.repository.get_count(poi_status="ACTIVE")
        return PoiPage(items=items, total=total, offset=offset, limit=limit)

    def get_poi(self, poi_id: str) -> PointOfInterest:
        poi = self.repository.get_by_id(poi_id, active_only=True)
        if poi is None:
            raise ResourceNotFound("POI not found")
        return poi


class PointOfInterestService:
    def __init__(
        self, session: Session, repository: PoiRepository,
        mappings: PoiCategoryMappingRepository, contents: PoiContentRepository,
        audios: ContentAudioRepository, categories: PoiCategoryRepository,
        regions: RegionRepository,
        image_checksums: RemoteImageChecksumProvider,
    ):
        self.session = session
        self.repository = repository
        self.mappings = mappings
        self.contents = contents
        self.audios = audios
        self.categories = categories
        self.regions = regions
        self.image_checksums = image_checksums

    def get_options(self) -> PoiFormOptions:
        """Lấy Region và Category tham chiếu cho form quản trị POI."""
        return PoiFormOptions(
            regions=self.regions.get_choices(),
            categories=self.categories.get_choices(),
        )

    def list_pois(
        self, *, offset: int, limit: int, search: str | None = None,
        poi_status: str | None = None, region_id: str | None = None, category_id: str | None = None,
    ) -> AdminPoiPage:
        """Tìm và lọc POI quản trị với phân trang ổn định."""
        if offset < 0 or not 1 <= limit <= 100:
            raise InvalidPoiFilter("offset must be >= 0 and limit must be between 1 and 100")
        if search is not None:
            search = search.strip()
            if not search or len(search) > 255:
                raise InvalidPoiFilter("search must contain between 1 and 255 characters")
        filters = {
            "search": search,
            "poi_status": poi_status,
            "region_id": region_id,
            "category_id": category_id,
        }
        pois = self.repository.get_all(
            offset=offset,
            limit=limit,
            sort_by="created_at",
            **filters,
        )
        total = self.repository.get_count(**filters)
        return AdminPoiPage(items=self._responses(pois), total=total, offset=offset, limit=limit)

    def get_poi(self, poi_id: str) -> AdminPoiRead:
        """Lấy chi tiết một POI cho màn hình quản trị."""
        poi = self._require_poi(poi_id)
        return self._responses([poi])[0]

    def create_poi(self, payload: PoiCreate, *, actor_id: str) -> AdminPoiRead:
        """Tạo POI INACTIVE cùng category mapping trong một transaction."""
        image_checksum = self.image_checksums.calculate(payload.poi_image_url)
        try:
            with self.session.begin():
                self._require_references(payload.region_id, payload.category_ids)
                now = datetime.now(timezone.utc)
                poi_id = generate_dated_identifier("poi", now)
                poi = PointOfInterest(
                    id=poi_id,
                    **payload.model_dump(exclude={"category_ids", "poi_status"}),
                    image_checksum_sha256=image_checksum,
                    poi_qr_code=create_poi_qr_payload(poi_id),
                    poi_status="INACTIVE", created_by=actor_id, last_updated_by=actor_id,
                    created_at=now, last_updated_at=now,
                )
                self.repository.add(poi)
                # UNIQUE constraint là nguồn kiểm tra cuối cùng, tránh race condition
                # giữa bước kiểm tra trước và hai request tạo đồng thời.
                self.session.flush()
                self.mappings.replace_for_poi(poi.id, payload.category_ids)
                self.session.flush()
                result = self._responses([poi])[0]
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return result

    def update_poi(self, poi_id: str, payload: PoiUpdate, *, actor_id: str) -> AdminPoiRead:
        """Cập nhật POI và mapping sau khi khóa dòng POI hiện tại."""
        image_checksum = None
        if "poi_image_url" in payload.model_fields_set:
            image_checksum = self.image_checksums.calculate(payload.poi_image_url)
        try:
            with self.session.begin():
                poi = self._require_poi(poi_id, for_update=True)
                values = payload.model_dump(exclude_unset=True)
                if image_checksum is not None:
                    values["image_checksum_sha256"] = image_checksum
                category_ids = values.pop("category_ids", None)
                target_status = values.pop("poi_status", None)
                self._require_references(values.get("region_id", poi.region_id), category_ids)
                remains_active = target_status == "ACTIVE" or (target_status is None and poi.poi_status == "ACTIVE")
                if remains_active and poi.id not in self._get_activatable_ids([poi.id]):
                    raise PoiConflict("An ACTIVE POI requires published English content with valid audio metadata")
                changed = any(getattr(poi, name) != value for name, value in values.items())
                for name, value in values.items():
                    setattr(poi, name, value)
                if target_status is not None:
                    changed = changed or poi.poi_status != target_status
                    poi.poi_status = target_status
                if category_ids is not None:
                    current_ids = self.mappings.get_category_ids_by_poi_ids([poi.id])[
                        poi.id
                    ]
                    if set(current_ids) != set(category_ids):
                        self.mappings.replace_for_poi(poi.id, category_ids)
                        changed = True
                if changed:
                    poi.last_updated_by = actor_id
                    poi.last_updated_at = datetime.now(timezone.utc)
                self.session.flush()
                result = self._responses([poi])[0]
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return result

    def _require_poi(self, poi_id: str, *, for_update: bool = False) -> PointOfInterest:
        poi = self.repository.get_by_id(poi_id, for_update=for_update)
        if poi is None:
            raise PoiNotFound("POI not found")
        return poi

    def _require_references(self, region_id: str, category_ids: list[str] | None) -> None:
        if self.regions.get_by_id(region_id) is None:
            raise PoiReferenceNotFound("Region not found")
        if category_ids is not None:
            missing = set(category_ids) - self.categories.get_existing_ids(category_ids)
            if missing:
                raise PoiReferenceNotFound("Unknown category IDs: " + ", ".join(sorted(missing)))

    def _responses(self, pois: list[PointOfInterest]) -> list[AdminPoiRead]:
        if not pois:
            return []
        ids = [poi.id for poi in pois]
        mappings = self.mappings.get_category_ids_by_poi_ids(ids)
        activatable = self._get_activatable_ids(ids)
        results = []
        for poi in pois:
            values = PoiRead.model_validate(poi).model_dump()
            values["poi_status"] = poi.poi_status
            results.append(AdminPoiRead(
                **values, created_by=poi.created_by, last_updated_by=poi.last_updated_by,
                category_ids=mappings[poi.id], can_activate=poi.id in activatable,
                qr_code_url=f"/api/v1/admin/pois/{poi.id}/qr-code",
            ))
        return results

    def _get_activatable_ids(self, poi_ids: list[str]) -> set[str]:
        contents = self.contents.get_published_english_contents(poi_ids)
        if not contents:
            return set()
        available_content_ids = self.audios.get_content_ids_with_valid_audio(list(contents))
        return {contents[content_id] for content_id in available_content_ids}

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> None:
        name = get_constraint_name(exc)
        if name == "point_of_interest_poi_qr_code_key":
            raise PoiConflict("poi_qr_code already exists") from exc
        if name == "uq_point_of_interest_location":
            raise PoiConflict("poi_location already exists") from exc
        if name in {"point_of_interest_region_id_fkey", "poi_category_mapping_poi_category_id_fkey"}:
            raise PoiReferenceNotFound("The selected region or category no longer exists") from exc
        raise exc
