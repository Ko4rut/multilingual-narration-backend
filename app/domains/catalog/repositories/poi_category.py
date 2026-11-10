from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.catalog.models.poi_category import PoiCategory


class PoiCategoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[PoiCategory]:
        return list(
            self.session.scalars(select(PoiCategory).order_by(PoiCategory.id))
        )
