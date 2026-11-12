from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.poi.exceptions import (
    InvalidPoiFilter,
    NarrationNotFound,
    PoiConflict,
    PoiNotFound,
    PoiReferenceNotFound,
)
from app.domains.poi.models.content_audio import ContentAudio
from app.domains.poi.models.poi_content import PoiContent
from app.domains.poi.models.point_of_interest import PointOfInterest
from app.domains.poi.repositories.content_audio import ContentAudioRepository
from app.domains.poi.repositories.poi_content import PoiContentRepository
from app.domains.poi.repositories.point_of_interest import PoiRepository
from app.domains.poi.schemas.content_audio import (
    AdminContentAudioRead,
    AudioMetadataWrite,
    ContentAudioPage,
)
from app.domains.poi.utils import generate_dated_identifier, get_constraint_name


class ContentAudioService:
    """Quản lý metadata audio tương ứng với ``ContentAudioRepository``."""

    def __init__(
        self,
        session: Session,
        pois: PoiRepository,
        contents: PoiContentRepository,
        audios: ContentAudioRepository,
    ):
        self.session = session
        self.pois = pois
        self.contents = contents
        self.audios = audios

    def list_audios(
        self,
        *,
        offset: int,
        limit: int,
        poi_id: str | None = None,
        language_id: str | None = None,
        poi_content_id: str | None = None,
        audio_source_type: str | None = None,
        search: str | None = None,
    ) -> ContentAudioPage:
        search = self._validate_filters(offset, limit, search)
        filters = {
            "poi_id": poi_id,
            "language_id": language_id,
            "poi_content_id": poi_content_id,
            "audio_source_type": audio_source_type,
            "search": search,
        }
        items = self.audios.get_all(offset=offset, limit=limit, **filters)
        total = self.audios.get_count(**filters)
        return ContentAudioPage(
            items=[AdminContentAudioRead.model_validate(item) for item in items],
            total=total,
            offset=offset,
            limit=limit,
        )

    def get_audio(self, audio_id: str) -> AdminContentAudioRead:
        audio = self.audios.get_by_id(audio_id)
        if audio is None:
            raise NarrationNotFound("Audio not found")
        return AdminContentAudioRead.model_validate(audio)

    def get_content_audio(self, content_id: str) -> AdminContentAudioRead:
        self._require_content(content_id)
        audio = self.audios.get_for_content(content_id)
        if audio is None:
            raise NarrationNotFound("Audio not found")
        return AdminContentAudioRead.model_validate(audio)

    def save_audio(
        self,
        content_id: str,
        payload: AudioMetadataWrite,
    ) -> AdminContentAudioRead:
        try:
            with self.session.begin():
                poi, content = self._lock_content(content_id)
                self._require_status(
                    content,
                    {"DRAFT", "REJECTED", "APPROVED", "PUBLISHED"},
                )
                audio = self.audios.get_for_content(content.id, for_update=True)
                now = datetime.now(timezone.utc)
                if audio is None:
                    audio = ContentAudio(
                        id=generate_dated_identifier("audio", now),
                        poi_content_id=content.id,
                        **payload.model_dump(),
                        created_at=now,
                        last_updated_at=now,
                    )
                    self.audios.add(audio)
                else:
                    if audio.audio_url != payload.audio_url:
                        raise PoiConflict(
                            "Audio asset URL is immutable; use a verified upload/import "
                            "workflow for a new asset"
                        )
                    if (
                        audio.audio_checksum_sha256.lower()
                        != payload.audio_checksum_sha256
                    ):
                        raise PoiConflict(
                            "Stored audio checksum cannot be changed without replacing the asset"
                        )
                    for name, value in payload.model_dump().items():
                        setattr(audio, name, value)
                    audio.last_updated_at = now
                self.session.flush()
                self._ensure_active_english(poi)
                result = AdminContentAudioRead.model_validate(audio)
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return result

    def _require_content(self, content_id: str) -> PoiContent:
        content = self.contents.get_by_id(content_id)
        if content is None:
            raise NarrationNotFound("Narration content not found")
        return content

    def _lock_content(
        self,
        content_id: str,
    ) -> tuple[PointOfInterest, PoiContent]:
        initial = self._require_content(content_id)
        poi = self.pois.get_by_id(initial.poi_id, for_update=True)
        if poi is None:
            raise PoiNotFound("POI not found")
        content = self.contents.get_by_id(content_id, for_update=True)
        if content is None:
            raise NarrationNotFound("Narration content not found")
        return poi, content

    def _ensure_active_english(self, poi: PointOfInterest) -> None:
        if poi.poi_status == "ACTIVE":
            versions = self.contents.get_published_english_contents([poi.id])
            if not self.audios.get_content_ids_with_valid_audio(list(versions)):
                raise PoiConflict(
                    "An ACTIVE POI must retain published English content with valid audio"
                )

    @staticmethod
    def _require_status(content: PoiContent, allowed: set[str]) -> None:
        if content.content_status.upper() not in allowed:
            raise PoiConflict(
                "Content state must be one of: " + ", ".join(sorted(allowed))
            )

    @staticmethod
    def _validate_filters(
        offset: int,
        limit: int,
        search: str | None,
    ) -> str | None:
        if offset < 0 or not 1 <= limit <= 100:
            raise InvalidPoiFilter(
                "offset must be >= 0 and limit must be between 1 and 100"
            )
        if search is not None:
            search = search.strip()
            if not search or len(search) > 255:
                raise InvalidPoiFilter(
                    "search must contain between 1 and 255 characters"
                )
        return search

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> None:
        name = get_constraint_name(exc)
        if name == "uq_content_audio_content":
            raise PoiConflict("This content already has an audio record") from exc
        if name == "content_audio_poi_content_id_fkey":
            raise PoiReferenceNotFound(
                "The selected narration content no longer exists"
            ) from exc
        if name == "offline_package_item_audio_id_fkey":
            raise PoiConflict(
                "Audio is referenced by an offline package"
            ) from exc
        raise exc
