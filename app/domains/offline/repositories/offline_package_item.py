"""Offline package membership and eligible published content selection."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.offline.models.offline_package_item import OfflinePackageItem
from app.domains.poi.models.point_of_interest import PointOfInterest
from app.domains.poi.models.poi_category_mapping import PoiCategoryMapping
from app.domains.poi.models.poi_content import PoiContent
from app.domains.poi.models.content_audio import ContentAudio


@dataclass(frozen=True)
class OfflineCandidate:
    poi: PointOfInterest
    content: PoiContent
    audio: ContentAudio


class OfflinePackageItemRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_by_package(self, package_id: str) -> list[OfflinePackageItem]:
        statement = (
            select(OfflinePackageItem)
            .where(OfflinePackageItem.package_id == package_id)
            .order_by(OfflinePackageItem.poi_id, OfflinePackageItem.poi_content_id)
        )
        return list(self.session.scalars(statement))

    def select_candidates(
        self, *, region_id: str, language_id: str, category_id: str | None = None,
    ) -> list[OfflineCandidate]:
        """Choose exact-language PUBLISHED content with valid audio metadata.

        This is a metadata-only eligibility check. Actual asset HTTP reachability
        and byte-level checksum verification must happen before publication.
        """
        stmt = (
            select(PointOfInterest, PoiContent, ContentAudio)
            .join(PoiContent, PoiContent.poi_id == PointOfInterest.id)
            .join(ContentAudio, ContentAudio.poi_content_id == PoiContent.id)
            .where(
                PointOfInterest.region_id == region_id,
                func.lower(PointOfInterest.poi_status) == "active",
                PoiContent.language_id == language_id,
                func.upper(PoiContent.content_status) == "PUBLISHED",
                ContentAudio.audio_size > 0,
                ContentAudio.audio_duration_sec > 0,
                ContentAudio.audio_url.regexp_match(r"^https?://[^/\s]+"),
                ContentAudio.audio_checksum_sha256.regexp_match(r"^[0-9a-fA-F]{64}$"),
                ContentAudio.audio_mime_type.in_((
                    "audio/mpeg", "audio/aac", "audio/ogg",
                    "audio/wav", "audio/mp4", "audio/webm",
                )),
                func.upper(ContentAudio.audio_source_type).in_((
                    "RECORD", "TTS", "PRE_GENERATED", "TTS_GENERATED",
                )),
            )
        )
        if category_id is not None:
            stmt = stmt.where(
                select(PoiCategoryMapping.poi_id).where(
                    PoiCategoryMapping.poi_id == PointOfInterest.id,
                    PoiCategoryMapping.poi_category_id == category_id,
                ).exists()
            )
        stmt = stmt.order_by(PointOfInterest.id, PoiContent.id, ContentAudio.id)
        return [
            OfflineCandidate(poi=poi, content=content, audio=audio)
            for poi, content, audio in self.session.execute(stmt).all()
        ]

    def add_all(self, items: list[OfflinePackageItem]) -> None:
        """Stage membership; caller must hold package lock and commit."""
        if len({item.poi_content_id for item in items}) != len(items):
            raise ValueError("Duplicate content membership in offline package")
        self.session.add_all(items)
