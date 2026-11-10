from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domains.catalog.models.language import Language, LanguageStatus


class LanguageRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_supported(self) -> list[Language]:
        return list(
            self.session.scalars(
                select(Language)
                .where(Language.language_status == LanguageStatus.SUPPORTED)
                .order_by(Language.id)
            )
        )

    def list_all(self) -> list[Language]:
        return list(self.session.scalars(select(Language).order_by(Language.id)))

    def get_by_id(self, language_id: str) -> Language | None:
        return self.session.get(Language, language_id)

    def find_conflict(
        self,
        *,
        language_code: str | None = None,
        language_name: str | None = None,
        exclude_id: str | None = None,
    ) -> Language | None:
        conditions = []
        if language_code is not None:
            conditions.append(Language.language_code == language_code)
        if language_name is not None:
            conditions.append(Language.language_name == language_name)
        statement = select(Language).where(or_(*conditions))
        if exclude_id is not None:
            statement = statement.where(Language.id != exclude_id)
        return self.session.scalar(statement.limit(1))

    def add(self, language: Language) -> None:
        self.session.add(language)
