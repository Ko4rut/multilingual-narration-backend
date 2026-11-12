from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.poi.exceptions import (
    InvalidPoiFilter,
    InvalidPoiQrCode,
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
)
from app.domains.poi.schemas.poi_content import (
    AdminPoiContentRead,
    PoiContentCreate,
    PoiContentOptions,
    PoiContentPage,
    PoiContentReview,
    PoiContentUpdate,
    PublishedNarration,
    QrNarrationRead,
)
from app.domains.poi.schemas.point_of_interest import PoiRead
from app.domains.poi.providers.qr_code import parse_poi_qr_payload
from app.domains.poi.providers.tts import (
    FileSystemTtsStorage,
    GttsSynthesizer,
    StoredTtsAudio,
)
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
                # Bước 1: Khóa POI cha để tuần tự hóa việc cấp version.
                self._lock_poi(payload.poi_id)
                # Bước 2: Kiểm tra Language, cấp version và tạo content DRAFT.
                content = self._new_content(
                    payload.poi_id, payload.language_id, payload.narration_title,
                    payload.narration_script, actor_id,
                )
                # Bước 3: Flush để database kiểm tra FK và version duy nhất.
                self.session.flush()
                # Bước 4: Trả content vừa tạo sau khi transaction thành công.
                result = self._content_responses([content])[0]
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return result

    def update_content(self, content_id: str, payload: PoiContentUpdate) -> AdminPoiContentRead:
        try:
            with self.session.begin():
                # Bước 1: Khóa POI và content cần chỉnh sửa.
                poi, content = self._lock_content(content_id)
                # Bước 2: Chỉ DRAFT/REJECTED mới được sửa trực tiếp.
                self._require_status(content, {"DRAFT", "REJECTED"})
                values = payload.model_dump(exclude_unset=True)
                # Bước 3: Content đã gắn audio phải tạo version mới thay vì sửa.
                if any(getattr(content, name) != value for name, value in values.items()):
                    if self.audios.get_for_content(content.id) is not None:
                        raise PoiConflict(
                            "Content with audio cannot be edited; create new content "
                            "for the same POI and language"
                        )
                # Bước 4: Áp dụng nội dung mới và đưa REJECTED trở lại DRAFT.
                for name, value in values.items():
                    setattr(content, name, value)
                content.content_status = "DRAFT"
                self._clear_review_fields(content)
                # Bước 5: Flush và bảo vệ điều kiện của POI đang ACTIVE.
                self.session.flush()
                self._ensure_active_english(poi)
                result = self._content_responses([content])[0]
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return result

    def submit_content(self, content_id: str) -> AdminPoiContentRead:
        with self.session.begin():
            # Bước 1: Khóa POI/content và kiểm tra trạng thái nguồn.
            _, content = self._lock_content(content_id)
            self._require_status(content, {"DRAFT", "REJECTED"})
            # Bước 2: Chuyển sang WAITING_APPROVAL và xóa metadata cũ.
            content.content_status = "WAITING_APPROVAL"
            self._clear_review_fields(content)
            # Bước 3: Flush rồi trả content đã submit.
            self.session.flush()
            result = self._content_responses([content])[0]
        return result

    def review_content(
        self, content_id: str, payload: PoiContentReview, *, actor_id: str,
    ) -> AdminPoiContentRead:
        """Phê duyệt hoặc từ chối content trong cùng một use case review."""
        with self.session.begin():
            # Bước 1: Khóa POI/content đang chờ duyệt.
            _, content = self._lock_content(content_id)
            self._require_status(content, {"WAITING_APPROVAL"})
            # Bước 2: Áp dụng quyết định APPROVE hoặc REJECT.
            # Phiên bản demo cho phép tác giả tự duyệt bằng cùng một tài khoản.
            if payload.decision == "APPROVE":
                content.content_status = "APPROVED"
                content.approved_by = actor_id
                content.approved_at = datetime.now(timezone.utc)
            else:
                content.content_status = "REJECTED"
                self._clear_review_fields(content)
            # Bước 3: Flush và trả trạng thái review mới.
            self.session.flush()
            result = self._content_responses([content])[0]
        return result

    def publish_content(self, content_id: str, *, actor_id: str) -> AdminPoiContentRead:
        generated_audio: StoredTtsAudio | None = None
        snapshot: tuple[str, str, str, str] | None = None

        # Bước 1: Khóa content, kiểm tra APPROVED/Language và chụp snapshot.
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

        # Bước 2: Nếu thiếu audio, sinh và lưu TTS ngoài transaction database.
        if snapshot is not None:
            generated = self.tts.synthesize(
                f"{snapshot[1]}. {snapshot[2]}", snapshot[3],
            )
            generated_audio = self.tts_storage.store(generated)

        try:
            with self.session.begin():
                # Bước 3: Khóa lại POI/content trước khi ghi kết quả publish.
                poi, content = self._lock_content(content_id)
                self._require_status(content, {"APPROVED"})
                self._require_supported_language(content.language_id)
                # Bước 4: Hủy publish nếu content đổi trong lúc tạo TTS.
                if snapshot is not None and snapshot[:3] != (
                    content.language_id,
                    content.narration_title,
                    content.narration_script,
                ):
                    raise PoiConflict("Content changed while TTS was being generated")
                # Bước 5: Tạo/cập nhật ContentAudio từ file TTS khi cần.
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
                # Bước 6: Khóa và archive phiên bản PUBLISHED cũ.
                previous = self.contents.get_published_versions(poi.id, content.language_id)
                if any(item.content_version >= content.content_version for item in previous):
                    raise PoiConflict("Cannot replace a published version with an older version")
                for item in previous:
                    item.content_status = "ARCHIVED"
                # Free the partial unique index first, within the same transaction.
                self.session.flush()
                # Bước 7: Publish phiên bản mới và ghi người/thời điểm thực hiện.
                content.content_status = "PUBLISHED"
                content.published_by = actor_id
                content.published_at = datetime.now(timezone.utc)
                self.session.flush()
                # Bước 8: Bảo đảm POI ACTIVE vẫn có English narration khả dụng.
                self._ensure_active_english(poi)
                result = self._content_responses([content])[0]
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return result

    def get_narration(self, poi_id: str, language_code: str) -> PublishedNarration:
        # Bước 1: Chỉ phục vụ POI đang ACTIVE.
        if self.pois.get_by_id(poi_id, active_only=True) is None:
            raise PoiNotFound("POI not found")
        return self._get_published_narration(poi_id, language_code)

    def resolve_qr(self, qr_code: str, language_code: str) -> QrNarrationRead:
        """Xác thực QR rồi trả POI ACTIVE cùng narration sẵn sàng phát."""
        # Bước 1: Chỉ chấp nhận deep-link QR do hệ thống phát hành.
        poi_id = parse_poi_qr_payload(qr_code)
        if poi_id is None:
            raise InvalidPoiQrCode("Invalid POI QR code")
        # Bước 2: Server online là nguồn quyết định POI còn ACTIVE hay không.
        poi = self.pois.get_by_id(poi_id, active_only=True)
        if poi is None:
            raise PoiNotFound("POI not found")
        # Bước 3: Chọn narration theo ngôn ngữ yêu cầu và fallback tiếng Anh.
        narration = self._get_published_narration(poi_id, language_code)
        return QrNarrationRead(
            poi=PoiRead.model_validate(poi),
            narration=narration,
        )

    def _get_published_narration(
        self, poi_id: str, language_code: str,
    ) -> PublishedNarration:
        # Bước 1: Chuẩn hóa ngôn ngữ và thêm tiếng Anh làm fallback.
        requested = language_code.lower()
        languages = list(dict.fromkeys((requested, "en")))
        for selected in languages:
            # Bước 2: Lấy các bản PUBLISHED theo thứ tự version mới nhất.
            contents = self.contents.get_published_for_language(poi_id, selected)
            ids = [content.id for content in contents]
            valid_ids = self.audios.get_content_ids_with_valid_audio(ids)
            audios = self.audios.get_for_contents(list(valid_ids))
            for content in contents:
                if content.id in valid_ids:
                    # Bước 3: Trả bản đầu tiên có audio hợp lệ và đánh dấu fallback.
                    return PublishedNarration(
                        poi_id=poi_id, content_id=content.id, language_code=selected,
                        requested_language_code=requested, is_fallback=selected != requested,
                        narration_title=content.narration_title, narration_script=content.narration_script,
                        content_version=content.content_version,
                        audio=AdminContentAudioRead.model_validate(audios[content.id]),
                    )
        # Bước 4: Không có cả ngôn ngữ yêu cầu lẫn tiếng Anh khả dụng.
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
