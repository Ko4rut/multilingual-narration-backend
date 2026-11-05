from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domains.poi.models.content_audio import ContentAudio
from app.domains.poi.models.poi_content import PoiContent
from app.domains.offline.models.offline_package_item import OfflinePackageItem


class ContentAudioRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_content_ids_with_valid_audio(self, content_ids: list[str]) -> set[str]:
        """Check audio metadata without making storage/network requests."""
        statement = select(ContentAudio.poi_content_id).distinct().where(
            ContentAudio.poi_content_id.in_(content_ids),
            ContentAudio.audio_url.regexp_match(r"^https?://[^/\s]+"),
            ContentAudio.audio_size > 0,
            ContentAudio.audio_duration_sec > 0,
            ContentAudio.audio_mime_type.in_((
                "audio/mpeg", "audio/aac", "audio/ogg", "audio/wav", "audio/mp4", "audio/webm",
            )),
            ContentAudio.audio_checksum_sha256.regexp_match(r"^[0-9a-fA-F]{64}$"),
            # Accept the existing seed aliases alongside the GROUP 2 names.
            func.upper(ContentAudio.audio_source_type).in_((
                "RECORD", "TTS", "PRE_GENERATED", "TTS_GENERATED",
            )),
        )
        return set(self.session.scalars(statement))

    def get_by_id(self, audio_id: str) -> ContentAudio | None:
        return self.session.get(ContentAudio, audio_id)

    def get_for_content(self, content_id: str, *, for_update: bool = False) -> ContentAudio | None:
        statement = select(ContentAudio).where(ContentAudio.poi_content_id == content_id)
        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(statement)

    def get_for_contents(self, content_ids: list[str]) -> dict[str, ContentAudio]:
        return {audio.poi_content_id: audio for audio in self.session.scalars(
            select(ContentAudio).where(ContentAudio.poi_content_id.in_(content_ids))
        )}

    def get_page(
        self, *, offset: int, limit: int, poi_id: str | None,
        language_id: str | None, poi_content_id: str | None,
        audio_source_type: str | None, search: str | None,
    ) -> tuple[list[ContentAudio], int]:
        filters = []
        if poi_id is not None:
            filters.append(PoiContent.poi_id == poi_id)
        if language_id is not None:
            filters.append(PoiContent.language_id == language_id)
        if poi_content_id is not None:
            filters.append(ContentAudio.poi_content_id == poi_content_id)
        if audio_source_type is not None:
            aliases = {"RECORD": ("RECORD", "PRE_GENERATED"), "TTS": ("TTS", "TTS_GENERATED")}
            filters.append(func.upper(ContentAudio.audio_source_type).in_(aliases[audio_source_type]))
        if search is not None:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            filters.append(or_(
                ContentAudio.id.ilike(pattern, escape="\\"),
                PoiContent.narration_title.ilike(pattern, escape="\\"),
            ))
        joined = select(ContentAudio).join(PoiContent, PoiContent.id == ContentAudio.poi_content_id).where(*filters)
        total = self.session.scalar(select(func.count()).select_from(joined.subquery()))
        items = list(self.session.scalars(
            joined.order_by(ContentAudio.created_at.desc(), ContentAudio.id).offset(offset).limit(limit)
        ))
        return items, total

    def has_external_references(self, audio_id: str) -> bool:
        return self.session.scalar(select(OfflinePackageItem.id).where(
            OfflinePackageItem.audio_id == audio_id,
        ).limit(1)) is not None

    def add(self, audio: ContentAudio) -> None:
        self.session.add(audio)

    def delete(self, audio: ContentAudio) -> None:
        self.session.delete(audio)
