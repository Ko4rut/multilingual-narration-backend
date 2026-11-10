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

    def get_choices(self) -> list[PoiCategory]:
        """Lấy danh mục cho form theo tên rồi ID để có thứ tự ổn định."""
        return list(
            self.session.scalars(
                select(PoiCategory).order_by(
                    PoiCategory.category_name,
                    PoiCategory.id,
                )
            )
        )

    def get_existing_ids(self, category_ids: list[str]) -> set[str]:
        """Trả về các ID danh mục thực sự tồn tại trong danh sách đầu vào."""
        if not category_ids:
            return set()
        return set(
            self.session.scalars(
                select(PoiCategory.id).where(PoiCategory.id.in_(category_ids))
            )
        )
