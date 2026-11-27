"""SQL-only persistence methods; the Catalog service owns transactions."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domains.catalog.models.poi_category import PoiCategory
from app.domains.offline.models.offline_package import OfflinePackage
from app.domains.poi.models.poi_category_mapping import PoiCategoryMapping


class PoiCategoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[PoiCategory]:
        return list(self.session.scalars(select(PoiCategory).order_by(PoiCategory.id)))

    def get_choices(self) -> list[PoiCategory]:
        """Order options by name and ID for deterministic admin and POI forms."""
        return list(
            self.session.scalars(
                select(PoiCategory).order_by(
                    PoiCategory.category_name, PoiCategory.id,
                )
            )
        )

    def get_existing_ids(self, category_ids: list[str]) -> set[str]:
        if not category_ids:
            return set()
        return set(
            self.session.scalars(
                select(PoiCategory.id).where(PoiCategory.id.in_(category_ids))
            )
        )

    def get_by_id(self, category_id: str, *, for_update: bool = False) -> PoiCategory | None:
        return self.session.get(PoiCategory, category_id, with_for_update=for_update)

    def get_conflict(
        self, *, category_name: str | None = None, category_code: str | None = None,
        exclude_id: str | None = None,
    ) -> PoiCategory | None:
        conditions = []
        if category_name is not None:
            conditions.append(func.lower(PoiCategory.category_name) == category_name.lower())
        if category_code is not None:
            conditions.append(func.lower(PoiCategory.category_code) == category_code.lower())
        if not conditions:
            return None
        statement = select(PoiCategory).where(or_(*conditions))
        if exclude_id is not None:
            statement = statement.where(PoiCategory.id != exclude_id)
        return self.session.scalar(statement.limit(1))

    def is_referenced(self, category_id: str) -> bool:
        """Guard deletion, including the POI link whose historical FK was CASCADE."""
        poi_reference = self.session.scalar(
            select(PoiCategoryMapping.poi_id)
            .where(PoiCategoryMapping.poi_category_id == category_id)
            .limit(1)
        )
        if poi_reference is not None:
            return True
        package_reference = self.session.scalar(
            select(OfflinePackage.id)
            .where(OfflinePackage.category_id == category_id)
            .limit(1)
        )
        return package_reference is not None

    def add(self, category: PoiCategory) -> None:
        self.session.add(category)

    def delete(self, category: PoiCategory) -> None:
        self.session.delete(category)
