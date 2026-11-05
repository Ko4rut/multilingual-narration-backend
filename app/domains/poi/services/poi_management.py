from datetime import datetime, timezone
from secrets import token_hex

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.poi.exceptions import (
    InvalidPoiFilter,
    PoiConflict,
    PoiNotFound,
    PoiReferenceNotFound,
)
from app.domains.poi.models.point_of_interest import PointOfInterest
from app.domains.poi.repositories.content_audio import ContentAudioRepository
from app.domains.poi.repositories.poi_category_mapping import PoiCategoryMappingRepository
from app.domains.poi.repositories.poi_content import PoiContentRepository
from app.domains.poi.repositories.point_of_interest import PoiRepository
from app.domains.poi.schemas.point_of_interest import (
    AdminPoiPage,
    AdminPoiRead,
    PoiCreate,
    PoiFormOptions,
    PoiRead,
    PoiUpdate,
)


class PoiAdminService:
    def __init__(
        self, session: Session, repository: PoiRepository,
        mappings: PoiCategoryMappingRepository, contents: PoiContentRepository,
        audios: ContentAudioRepository,
    ):
        self.session = session
        self.repository = repository
        self.mappings = mappings
        self.contents = contents
        self.audios = audios

    def get_options(self) -> PoiFormOptions:
        return PoiFormOptions(
            regions=self.repository.get_regions(), categories=self.mappings.get_categories(),
        )

    def list_pois(
        self, *, offset: int, limit: int, search: str | None = None,
        poi_status: str | None = None, region_id: str | None = None, category_id: str | None = None,
    ) -> AdminPoiPage:
        if offset < 0 or not 1 <= limit <= 100:
            raise InvalidPoiFilter("offset must be >= 0 and limit must be between 1 and 100")
        if search is not None:
            search = search.strip()
            if not search or len(search) > 255:
                raise InvalidPoiFilter("search must contain between 1 and 255 characters")
        pois, total = self.repository.get_page(
            offset=offset, limit=limit, search=search, poi_status=poi_status,
            region_id=region_id, category_id=category_id,
        )
        return AdminPoiPage(items=self._responses(pois), total=total, offset=offset, limit=limit)

    def get_poi(self, poi_id: str) -> AdminPoiRead:
        poi = self._require_poi(poi_id)
        return self._responses([poi])[0]

    def create_poi(self, payload: PoiCreate, *, actor_id: str) -> AdminPoiRead:
        try:
            with self.session.begin():
                self._require_references(payload.region_id, payload.category_ids)
                self._require_unique(payload.poi_qr_code, payload.poi_location)
                now = datetime.now(timezone.utc)
                poi = PointOfInterest(
                    id=f"poi-{now:%d%m%y}-{token_hex(4)}",
                    **payload.model_dump(exclude={"category_ids", "poi_status"}),
                    poi_status="inactive", created_by=actor_id, last_updated_by=actor_id,
                    created_at=now, last_updated_at=now,
                )
                self.repository.add(poi)
                self.session.flush()
                self.mappings.replace_categories(poi.id, payload.category_ids)
                self.session.flush()
                result = self._responses([poi])[0]
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return result

    def update_poi(self, poi_id: str, payload: PoiUpdate, *, actor_id: str) -> AdminPoiRead:
        try:
            with self.session.begin():
                poi = self._require_poi(poi_id, for_update=True)
                values = payload.model_dump(exclude_unset=True)
                category_ids = values.pop("category_ids", None)
                target_status = values.pop("poi_status", None)
                self._require_references(values.get("region_id", poi.region_id), category_ids)
                self._require_unique(
                    values.get("poi_qr_code", poi.poi_qr_code),
                    values.get("poi_location", poi.poi_location), exclude_id=poi.id,
                )
                remains_active = target_status == "ACTIVE" or (target_status is None and poi.poi_status == "active")
                if remains_active and poi.id not in self._get_activatable_ids([poi.id]):
                    raise PoiConflict("An ACTIVE POI requires published English content with valid audio metadata")
                if "poi_image_url" in values and values["poi_image_url"] != poi.poi_image_url:
                    values.setdefault("image_checksum_sha256", None)
                changed = any(getattr(poi, name) != value for name, value in values.items())
                for name, value in values.items():
                    setattr(poi, name, value)
                if target_status is not None:
                    stored_status = target_status.lower()
                    changed = changed or poi.poi_status != stored_status
                    poi.poi_status = stored_status
                if category_ids is not None:
                    current_ids = self.mappings.get_category_mappings([poi.id])[poi.id]
                    if set(current_ids) != set(category_ids):
                        self.mappings.replace_categories(poi.id, category_ids)
                        changed = True
                if changed:
                    poi.last_updated_by = actor_id
                    poi.last_updated_at = datetime.now(timezone.utc)
                self.session.flush()
                result = self._responses([poi])[0]
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return result

    def delete_poi(self, poi_id: str) -> None:
        try:
            with self.session.begin():
                poi = self._require_poi(poi_id, for_update=True)
                if self.contents.has_content(poi_id):
                    raise PoiConflict("POIs with linked content cannot be deleted; deactivate the POI instead")
                if self.repository.has_external_references(poi_id):
                    raise PoiConflict("POIs referenced by listening history or offline packages cannot be deleted")
                self.mappings.replace_categories(poi_id, [])
                self.repository.delete(poi)
                self.session.flush()
        except IntegrityError as exc:
            self._translate_integrity_error(exc)

    def _require_poi(self, poi_id: str, *, for_update: bool = False) -> PointOfInterest:
        poi = self.repository.get_by_id(poi_id, for_update=for_update)
        if poi is None:
            raise PoiNotFound("POI not found")
        return poi

    def _require_references(self, region_id: str, category_ids: list[str] | None) -> None:
        if not self.repository.region_exists(region_id):
            raise PoiReferenceNotFound("Region not found")
        if category_ids is not None:
            missing = set(category_ids) - self.mappings.get_existing_category_ids(category_ids)
            if missing:
                raise PoiReferenceNotFound("Unknown category IDs: " + ", ".join(sorted(missing)))

    def _require_unique(self, qr_code: str, location: str, *, exclude_id: str | None = None) -> None:
        for field, value in (("poi_qr_code", qr_code), ("poi_location", location)):
            if self.repository.has_duplicate(field, value, exclude_id=exclude_id):
                raise PoiConflict(f"{field} already exists")

    def _responses(self, pois: list[PointOfInterest]) -> list[AdminPoiRead]:
        if not pois:
            return []
        ids = [poi.id for poi in pois]
        mappings = self.mappings.get_category_mappings(ids)
        activatable = self._get_activatable_ids(ids)
        results = []
        for poi in pois:
            values = PoiRead.model_validate(poi).model_dump()
            values["poi_status"] = "ACTIVE" if poi.poi_status == "active" else "INACTIVE"
            results.append(AdminPoiRead(
                **values, created_by=poi.created_by, last_updated_by=poi.last_updated_by,
                category_ids=mappings[poi.id], can_activate=poi.id in activatable,
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
        name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if name == "point_of_interest_poi_qr_code_key":
            raise PoiConflict("poi_qr_code already exists") from exc
        if name == "uq_point_of_interest_location":
            raise PoiConflict("poi_location already exists") from exc
        if name in {"point_of_interest_region_id_fkey", "poi_category_mapping_poi_category_id_fkey"}:
            raise PoiReferenceNotFound("The selected region or category no longer exists") from exc
        if name in {"listening_history_poi_id_fkey", "offline_package_item_poi_id_fkey"}:
            raise PoiConflict("POI is referenced by listening history or an offline package") from exc
        raise exc
