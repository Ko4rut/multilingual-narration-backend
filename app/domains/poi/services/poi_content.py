from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.poi.exceptions import (
    InvalidPoiFilter,
    NarrationNotFound,
    PoiConflict,
    PoiNotFound,
    PoiPermissionDenied,
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
from app.domains.poi.schemas.poi_content import (
    AdminPoiContentRead,
    PoiContentCreate,
    PoiContentOptions,
    PoiContentPage,
    PoiContentReview,
    PoiContentUpdate,
    PublishedNarration,
)
from app.domains.poi.tts import FileSystemTtsStorage, GttsSynthesizer, StoredTtsAudio
from app.domains.poi.utils import generate_dated_identifier, get_constraint_name


class PoiContentService:
    """Narration lifecycle and attached audio; writes share the parent POI lock."""

    def __init__(
        self, session: Session, pois: PoiRepository,
        contents: PoiContentRepository, audios: ContentAudioRepository,
        tts: GttsSynthesizer | None = None,
        tts_storage: FileSystemTtsStorage | None = None,
    ):
        self.session = session
        self.pois = pois
        self.contents = contents
        self.audios = audios
        self.tts = tts
        self.tts_storage = tts_storage

    def get_options(self) -> PoiContentOptions:
        return PoiContentOptions(pois=self.pois.get_all(), languages=self.contents.get_languages())

    def list_contents(
        self, *, offset: int, limit: int, poi_id: str | None = None,
        language_id: str | None = None, content_status: str | None = None, search: str | None = None,
    ) -> PoiContentPage:
        search = self._validate_filters(offset, limit, search)
        filters = {
            "poi_id": poi_id,
            "language_id": language_id,
            "content_status": content_status,
            "search": search,
        }
        items = self.contents.get_all(
            offset=offset, limit=limit, **filters,
        )
        total = self.contents.get_count(**filters)
        return PoiContentPage(items=self._content_responses(items), total=total, offset=offset, limit=limit)

    def get_content(self, content_id: str) -> AdminPoiContentRead:
        return self._content_responses([self._require_content(content_id)])[0]

    def create_content(self, payload: PoiContentCreate, *, actor_id: str) -> AdminPoiContentRead:
        try:
            with self.session.begin():
                self._lock_poi(payload.poi_id)
                content = self._new_content(
                    payload.poi_id, payload.language_id, payload.narration_title,
                    payload.narration_script, actor_id,
                )
                self.session.flush()
                result = self._content_responses([content])[0]
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return result

    def update_content(self, content_id: str, payload: PoiContentUpdate) -> AdminPoiContentRead:
        try:
            with self.session.begin():
                poi, content = self._lock_content(content_id)
                self._require_status(content, {"DRAFT", "REJECTED"})
                values = payload.model_dump(exclude_unset=True)
                if any(getattr(content, name) != value for name, value in values.items()):
                    if self.audios.get_for_content(content.id) is not None:
                        raise PoiConflict(
                            "Content with audio cannot be edited; create new content "
                            "for the same POI and language"
                        )
                for name, value in values.items():
                    setattr(content, name, value)
                content.content_status = "DRAFT"
                self._clear_review_fields(content)
                self.session.flush()
                self._ensure_active_english(poi)
                result = self._content_responses([content])[0]
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return result

    def submit_content(self, content_id: str) -> AdminPoiContentRead:
        with self.session.begin():
            _, content = self._lock_content(content_id)
            self._require_status(content, {"DRAFT", "REJECTED"})
            content.content_status = "WAITING_APPROVAL"
            self._clear_review_fields(content)
            self.session.flush()
            result = self._content_responses([content])[0]
        return result

    def review_content(
        self, content_id: str, payload: PoiContentReview, *, actor_id: str,
    ) -> AdminPoiContentRead:
        """Phê duyệt hoặc từ chối content trong cùng một use case review."""
        with self.session.begin():
            _, content = self._lock_content(content_id)
            self._require_status(content, {"WAITING_APPROVAL"})
            if content.created_by == actor_id:
                raise PoiPermissionDenied("Authors cannot review their own content")
            if payload.decision == "APPROVE":
                content.content_status = "APPROVED"
                content.approved_by = actor_id
                content.approved_at = datetime.now(timezone.utc)
            else:
                content.content_status = "REJECTED"
                self._clear_review_fields(content)
            self.session.flush()
            result = self._content_responses([content])[0]
        return result

    def publish_content(self, content_id: str, *, actor_id: str) -> AdminPoiContentRead:
        generated_audio: StoredTtsAudio | None = None
        snapshot: tuple[str, str, str, str] | None = None

        # Đọc snapshot trong transaction riêng rồi gọi TTS ngoài transaction DB.
        # Transaction ghi bên dưới sẽ khóa và xác minh snapshot lại trước khi lưu.
        with self.session.begin():
            _, content = self._lock_content(content_id)
            self._require_status(content, {"APPROVED"})
            language = self._require_supported_language(content.language_id)
            if content.id not in self.audios.get_content_ids_with_valid_audio([content.id]):
                if self.tts is None or self.tts_storage is None:
                    raise PoiConflict("Publishing requires audio or configured TTS")
                snapshot = (
                    content.language_id,
                    content.narration_title,
                    content.narration_script,
                    language.language_code,
                )

        if snapshot is not None:
            generated = self.tts.synthesize(
                f"{snapshot[1]}. {snapshot[2]}", snapshot[3],
            )
            generated_audio = self.tts_storage.store(generated)

        try:
            with self.session.begin():
                poi, content = self._lock_content(content_id)
                self._require_status(content, {"APPROVED"})
                self._require_supported_language(content.language_id)
                if snapshot is not None and snapshot[:3] != (
                    content.language_id,
                    content.narration_title,
                    content.narration_script,
                ):
                    raise PoiConflict("Content changed while TTS was being generated")
                if content.id not in self.audios.get_content_ids_with_valid_audio([content.id]):
                    if generated_audio is None:
                        raise PoiConflict("Publishing requires valid audio metadata")
                    audio = self.audios.get_for_content(content.id, for_update=True)
                    now = datetime.now(timezone.utc)
                    values = {
                        "audio_url": generated_audio.url,
                        "audio_size": generated_audio.size,
                        "audio_source_type": "TTS",
                        "audio_duration_sec": generated_audio.duration_sec,
                        "audio_mime_type": "audio/mpeg",
                        "audio_checksum_sha256": generated_audio.checksum_sha256,
                    }
                    if audio is None:
                        audio = ContentAudio(
                            id=generate_dated_identifier("audio", now),
                            poi_content_id=content.id,
                            **values,
                            created_at=now,
                            last_updated_at=now,
                        )
                        self.audios.add(audio)
                    else:
                        for name, value in values.items():
                            setattr(audio, name, value)
                        audio.last_updated_at = now
                    self.session.flush()
                previous = self.contents.get_published_versions(poi.id, content.language_id)
                if any(item.content_version >= content.content_version for item in previous):
                    raise PoiConflict("Cannot replace a published version with an older version")
                for item in previous:
                    item.content_status = "ARCHIVED"
                # Free the partial unique index first, within the same transaction.
                self.session.flush()
                content.content_status = "PUBLISHED"
                content.published_by = actor_id
                content.published_at = datetime.now(timezone.utc)
                self.session.flush()
                self._ensure_active_english(poi)
                result = self._content_responses([content])[0]
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return result

    def list_audios(
        self, *, offset: int, limit: int, poi_id: str | None = None,
        language_id: str | None = None, poi_content_id: str | None = None,
        audio_source_type: str | None = None, search: str | None = None,
    ) -> ContentAudioPage:
        search = self._validate_filters(offset, limit, search)
        filters = {
            "poi_id": poi_id,
            "language_id": language_id,
            "poi_content_id": poi_content_id,
            "audio_source_type": audio_source_type,
            "search": search,
        }
        items = self.audios.get_all(
            offset=offset, limit=limit, **filters,
        )
        total = self.audios.get_count(**filters)
        return ContentAudioPage(
            items=[AdminContentAudioRead.model_validate(item) for item in items],
            total=total, offset=offset, limit=limit,
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

    def save_audio(self, content_id: str, payload: AudioMetadataWrite) -> AdminContentAudioRead:
        try:
            with self.session.begin():
                poi, content = self._lock_content(content_id)
                self._require_status(content, {"DRAFT", "REJECTED", "APPROVED", "PUBLISHED"})
                audio = self.audios.get_for_content(content.id, for_update=True)
                now = datetime.now(timezone.utc)
                if audio is None:
                    audio = ContentAudio(
                        id=generate_dated_identifier("audio", now),
                        poi_content_id=content.id,
                        **payload.model_dump(), created_at=now, last_updated_at=now,
                    )
                    self.audios.add(audio)
                else:
                    if audio.audio_url == payload.audio_url and audio.audio_checksum_sha256.lower() != payload.audio_checksum_sha256:
                        raise PoiConflict("Use a new immutable asset URL when the audio checksum changes")
                    for name, value in payload.model_dump().items():
                        setattr(audio, name, value)
                    audio.last_updated_at = now
                self.session.flush()
                self._ensure_active_english(poi)
                result = AdminContentAudioRead.model_validate(audio)
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return result

    def get_narration(self, poi_id: str, language_code: str) -> PublishedNarration:
        if self.pois.get_by_id(poi_id, active_only=True) is None:
            raise PoiNotFound("POI not found")
        requested = language_code.lower()
        languages = list(dict.fromkeys((requested, "en")))
        for selected in languages:
            contents = self.contents.get_published_for_language(poi_id, selected)
            ids = [content.id for content in contents]
            valid_ids = self.audios.get_content_ids_with_valid_audio(ids)
            audios = self.audios.get_for_contents(list(valid_ids))
            for content in contents:
                if content.id in valid_ids:
                    return PublishedNarration(
                        poi_id=poi_id, content_id=content.id, language_code=selected,
                        requested_language_code=requested, is_fallback=selected != requested,
                        narration_title=content.narration_title, narration_script=content.narration_script,
                        content_version=content.content_version,
                        audio=AdminContentAudioRead.model_validate(audios[content.id]),
                    )
        raise NarrationNotFound("No published narration with usable audio is available")

    def _new_content(self, poi_id: str, language_id: str, title: str, script: str, actor_id: str) -> PoiContent:
        self._require_supported_language(language_id)
        version = self.contents.get_next_version(poi_id, language_id)
        if version > 2_147_483_647:
            raise PoiConflict("Content version limit exceeded")
        now = datetime.now(timezone.utc)
        content = PoiContent(
            id=generate_dated_identifier("cont", now),
            poi_id=poi_id,
            language_id=language_id,
            narration_title=title, narration_script=script, content_version=version,
            content_status="DRAFT", created_by=actor_id, created_at=now,
        )
        self.contents.add(content)
        return content

    def _require_supported_language(self, language_id: str):
        language = self.contents.get_language(language_id)
        if language is None:
            raise PoiReferenceNotFound("Language not found")
        if language.language_status.lower() not in {"supported", "active"}:
            raise PoiConflict("The selected language is not supported for new content or publication")
        return language

    def _require_content(self, content_id: str) -> PoiContent:
        content = self.contents.get_by_id(content_id)
        if content is None:
            raise NarrationNotFound("Narration content not found")
        return content

    def _lock_poi(self, poi_id: str) -> PointOfInterest:
        poi = self.pois.get_by_id(poi_id, for_update=True)
        if poi is None:
            raise PoiNotFound("POI not found")
        return poi

    def _lock_content(self, content_id: str) -> tuple[PointOfInterest, PoiContent]:
        initial = self._require_content(content_id)
        poi = self._lock_poi(initial.poi_id)
        content = self.contents.get_by_id(content_id, for_update=True)
        if content is None:
            raise NarrationNotFound("Narration content not found")
        return poi, content

    def _ensure_active_english(self, poi: PointOfInterest) -> None:
        if poi.poi_status == "ACTIVE":
            versions = self.contents.get_published_english_contents([poi.id])
            if not self.audios.get_content_ids_with_valid_audio(list(versions)):
                raise PoiConflict("An ACTIVE POI must retain published English content with valid audio")

    def _content_responses(self, contents: list[PoiContent]) -> list[AdminPoiContentRead]:
        audios = self.audios.get_for_contents([item.id for item in contents])
        results = []
        for content in contents:
            audio = audios.get(content.id)
            result = AdminPoiContentRead.model_validate(content)
            if audio is not None:
                result.audio = AdminContentAudioRead.model_validate(audio)
            results.append(result)
        return results

    @staticmethod
    def _require_status(content: PoiContent, allowed: set[str]) -> None:
        if content.content_status.upper() not in allowed:
            raise PoiConflict("Content state must be one of: " + ", ".join(sorted(allowed)))

    @staticmethod
    def _clear_review_fields(content: PoiContent) -> None:
        content.approved_by = None
        content.approved_at = None
        content.published_by = None
        content.published_at = None

    @staticmethod
    def _validate_filters(offset: int, limit: int, search: str | None) -> str | None:
        if offset < 0 or not 1 <= limit <= 100:
            raise InvalidPoiFilter("offset must be >= 0 and limit must be between 1 and 100")
        if search is not None:
            search = search.strip()
            if not search or len(search) > 255:
                raise InvalidPoiFilter("search must contain between 1 and 255 characters")
        return search

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> None:
        name = get_constraint_name(exc)
        if name in {"uq_poi_content_poi_language_version", "uq_poi_content_published_language"}:
            raise PoiConflict("A conflicting narration version already exists; reload and retry") from exc
        if name == "uq_content_audio_content":
            raise PoiConflict("This content already has an audio record") from exc
        if name in {"poi_content_language_id_fkey", "poi_content_poi_id_fkey", "content_audio_poi_content_id_fkey"}:
            raise PoiReferenceNotFound("The selected POI, language or content no longer exists") from exc
        if name in {"listening_history_poi_content_id_fkey", "offline_package_item_poi_content_id_fkey", "offline_package_item_audio_id_fkey"}:
            raise PoiConflict("Content/audio is referenced by listening history or an offline package") from exc
        raise exc
