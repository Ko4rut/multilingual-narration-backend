from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.domains.catalog.models.language import Language, LanguageStatus
from app.domains.poi.models.poi_content import PoiContent
from app.domains.poi.utils import escape_like_value


class PoiContentRepository:
    def __init__(self, session: Session):
        self.session = session

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

    def get_all(
        self, *, offset: int, limit: int, poi_id: str | None,
        language_id: str | None, content_status: str | None, search: str | None,
    ) -> list[PoiContent]:
        """Lấy một trang nội dung theo các bộ lọc quản trị."""
        filters = self._get_filters(
            poi_id=poi_id,
            language_id=language_id,
            content_status=content_status,
            search=search,
        )
        return list(self.session.scalars(
            select(PoiContent).where(*filters)
            .order_by(PoiContent.created_at.desc(), PoiContent.id)
            .offset(offset).limit(limit)
        ))

    def get_count(
        self, *, poi_id: str | None, language_id: str | None,
        content_status: str | None, search: str | None,
    ) -> int:
        """Đếm nội dung theo cùng bộ lọc của ``get_all``."""
        filters = self._get_filters(
            poi_id=poi_id,
            language_id=language_id,
            content_status=content_status,
            search=search,
        )
        return self.session.scalar(
            select(func.count()).select_from(PoiContent).where(*filters)
        )

    @staticmethod
    def _get_filters(
        *, poi_id: str | None, language_id: str | None,
        content_status: str | None, search: str | None,
    ) -> list[ColumnElement[bool]]:
        """Tạo bộ lọc dùng chung cho danh sách và tổng số nội dung."""
        filters: list[ColumnElement[bool]] = []
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
        return filters

    def get_next_version(self, poi_id: str, language_id: str) -> int:
        """Lấy số phiên bản kế tiếp khi service đang giữ khóa POI cha."""
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

    def add(self, content: PoiContent) -> None:
        """Đưa content mới vào Session; service sở hữu transaction."""
        self.session.add(content)
