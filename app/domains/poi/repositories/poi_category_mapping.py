from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domains.catalog.models.poi_category import PoiCategory
from app.domains.poi.models.poi_category_mapping import PoiCategoryMapping


class PoiCategoryMappingRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_categories(self) -> list[PoiCategory]:
        return list(self.session.scalars(select(PoiCategory).order_by(PoiCategory.category_name, PoiCategory.id)))

    def get_existing_category_ids(self, category_ids: list[str]) -> set[str]:
        return set(self.session.scalars(select(PoiCategory.id).where(PoiCategory.id.in_(category_ids))))

    def get_category_mappings(self, poi_ids: list[str]) -> dict[str, list[str]]:
        mappings = {poi_id: [] for poi_id in poi_ids}
        rows = self.session.execute(
            select(PoiCategoryMapping.poi_id, PoiCategoryMapping.poi_category_id)
            .where(PoiCategoryMapping.poi_id.in_(poi_ids))
            .order_by(PoiCategoryMapping.poi_category_id)
        )
        for poi_id, category_id in rows:
            mappings[poi_id].append(category_id)
        return mappings

    def replace_categories(self, poi_id: str, category_ids: list[str]) -> None:
        self.session.execute(delete(PoiCategoryMapping).where(PoiCategoryMapping.poi_id == poi_id))
        self.session.add_all([
            PoiCategoryMapping(poi_id=poi_id, poi_category_id=category_id)
            for category_id in category_ids
        ])
