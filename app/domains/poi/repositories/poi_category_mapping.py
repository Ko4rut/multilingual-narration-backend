from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domains.poi.models.poi_category_mapping import PoiCategoryMapping


class PoiCategoryMappingRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_category_ids_by_poi_ids(
        self,
        poi_ids: list[str],
    ) -> dict[str, list[str]]:
        """Nhóm các ID danh mục theo từng POI mà không tạo truy vấn N+1."""
        mappings = {poi_id: [] for poi_id in poi_ids}
        if not poi_ids:
            return mappings
        rows = self.session.execute(
            select(PoiCategoryMapping.poi_id, PoiCategoryMapping.poi_category_id)
            .where(PoiCategoryMapping.poi_id.in_(poi_ids))
            .order_by(PoiCategoryMapping.poi_category_id)
        )
        for poi_id, category_id in rows:
            mappings[poi_id].append(category_id)
        return mappings

    def replace_for_poi(self, poi_id: str, category_ids: list[str]) -> None:
        """Thay toàn bộ mapping của một POI; service sở hữu transaction."""
        self.session.execute(
            delete(PoiCategoryMapping).where(PoiCategoryMapping.poi_id == poi_id)
        )
        self.session.add_all(
            [
                PoiCategoryMapping(
                    poi_id=poi_id,
                    poi_category_id=category_id,
                )
                for category_id in category_ids
            ]
        )
