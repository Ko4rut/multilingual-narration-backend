from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domains.catalog.models.language import Language, LanguageStatus
from app.domains.listening.models.listening_history import ListeningHistory
from app.domains.offline.models.offline_package_item import OfflinePackageItem
from app.domains.poi.models.poi_content import PoiContent
from app.domains.poi.utils import escape_like_value


class PoiContentRepository:
    def __init__(self, session: Session):
        self.session = session

    def has_content(self, poi_id: str) -> bool:
        statement = select(PoiContent.id).where(PoiContent.poi_id == poi_id).limit(1)
        return self.session.scalar(statement) is not None

    def get_published_english_contents(self, poi_ids: list[str]) -> dict[str, str]:
        """Map content ID to POI ID for the requested published English versions."""
        statement = (
            select(PoiContent.id, PoiContent.poi_id)
            .join(Language, Language.id == PoiContent.language_id)
            .where(
                PoiContent.poi_id.in_(poi_ids),
                func.lower(Language.language_code) == "en",
                func.upper(PoiContent.content_status) == "PUBLISHED",
            )
        )
        return dict(self.session.execute(statement).all())

    def get_by_id(self, content_id: str, *, for_update: bool = False) -> PoiContent | None:
        statement = select(PoiContent).where(PoiContent.id == content_id)
        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(statement)

    def get_page(
        self, *, offset: int, limit: int, poi_id: str | None,
        language_id: str | None, content_status: str | None, search: str | None,
    ) -> tuple[list[PoiContent], int]:
        filters = []
        if poi_id is not None:
            filters.append(PoiContent.poi_id == poi_id)
        if language_id is not None:
            filters.append(PoiContent.language_id == language_id)
        if content_status is not None:
            filters.append(func.upper(PoiContent.content_status) == content_status)
        if search is not None:
            escaped = escape_like_value(search)
            pattern = f"%{escaped}%"
            filters.append(or_(
                PoiContent.id.ilike(pattern, escape="\\"),
                PoiContent.narration_title.ilike(pattern, escape="\\"),
            ))
        total = self.session.scalar(select(func.count()).select_from(PoiContent).where(*filters))
        items = list(self.session.scalars(
            select(PoiContent).where(*filters)
            .order_by(PoiContent.created_at.desc(), PoiContent.id)
            .offset(offset).limit(limit)
        ))
        return items, total

    def next_version(self, poi_id: str, language_id: str) -> int:
        # The service must hold the parent POI lock before allocating a version.
        latest = self.session.scalar(select(func.max(PoiContent.content_version)).where(
            PoiContent.poi_id == poi_id, PoiContent.language_id == language_id,
        ))
        return (latest or 0) + 1

    def get_language(self, language_id: str) -> Language | None:
        return self.session.get(Language, language_id)

    def get_languages(self) -> list[Language]:
        return list(self.session.scalars(select(Language).order_by(Language.language_name, Language.id)))

    def get_published_versions(self, poi_id: str, language_id: str) -> list[PoiContent]:
        return list(self.session.scalars(
            select(PoiContent).where(
                PoiContent.poi_id == poi_id, PoiContent.language_id == language_id,
                func.upper(PoiContent.content_status) == "PUBLISHED",
            ).order_by(PoiContent.id).with_for_update().execution_options(populate_existing=True)
        ))

    def get_published_for_language(self, poi_id: str, language_code: str) -> list[PoiContent]:
        return list(self.session.scalars(
            select(PoiContent).join(Language, Language.id == PoiContent.language_id).where(
                PoiContent.poi_id == poi_id,
                func.lower(Language.language_code) == language_code,
                Language.language_status == LanguageStatus.SUPPORTED,
                func.upper(PoiContent.content_status) == "PUBLISHED",
            ).order_by(PoiContent.content_version.desc(), PoiContent.id)
        ))

    def has_external_references(self, content_id: str) -> bool:
        for model in (ListeningHistory, OfflinePackageItem):
            if self.session.scalar(select(model.id).where(model.poi_content_id == content_id).limit(1)) is not None:
                return True
        return False

    def add(self, content: PoiContent) -> None:
        self.session.add(content)

    def delete(self, content: PoiContent) -> None:
        self.session.delete(content)
