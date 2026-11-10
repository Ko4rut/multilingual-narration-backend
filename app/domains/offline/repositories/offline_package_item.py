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
                PointOfInterest.poi_status == "ACTIVE",
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
                ContentAudio.audio_source_type.in_(("RECORD", "TTS")),
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

    def sync_membership(
        self, *, package_id: str, candidates: list[OfflineCandidate],
        updated_at,
    ) -> None:
        """Synchronize current package membership, preserving unchanged item IDs.

        Call only after the complete new manifest and assets have been
        externally verified, inside the service's locked publication transaction.
        Never delete the referenced POI, Content, Audio or physical asset.
        """
        existing = {item.poi_content_id: item for item in self.list_by_package(package_id)}
        selected = {candidate.content.id: candidate for candidate in candidates}
        if len(selected) != len(candidates):
            raise ValueError("Duplicate content in package candidates")
        if len({candidate.poi.id for candidate in candidates}) != len(candidates):
            raise ValueError("Duplicate POI in package candidates")
        for content_id, item in existing.items():
            if content_id not in selected:
                self.session.delete(item)
        for content_id, candidate in selected.items():
            item = existing.get(content_id)
            if item is None:
                from datetime import datetime
                from secrets import token_hex

                item = OfflinePackageItem(
                    id=f"pack-item-{updated_at:%d%m%y}-{token_hex(4)}",
                    package_id=package_id,
                    poi_id=candidate.poi.id,
                    poi_content_id=content_id,
                    audio_id=candidate.audio.id,
                    content_version=candidate.content.content_version,
                    created_at=updated_at,
                    last_updated_at=updated_at,
                )
                self.session.add(item)
                continue
            if (
                item.poi_id != candidate.poi.id
                or item.audio_id != candidate.audio.id
                or item.content_version != candidate.content.content_version
            ):
                item.poi_id = candidate.poi.id
                item.audio_id = candidate.audio.id
                item.content_version = candidate.content.content_version
                item.last_updated_at = updated_at
