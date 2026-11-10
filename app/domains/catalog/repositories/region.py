from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.catalog.models.region import Region


class RegionRepository:
    """Đọc dữ liệu Region dùng chung cho Catalog và các domain tham chiếu."""

    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[Region]:
        """Lấy toàn bộ khu vực theo ID cho API Catalog."""
        return list(
            self.session.scalars(select(Region).order_by(Region.id))
        )

    def get_choices(self) -> list[Region]:
        """Lấy khu vực cho form theo tên rồi ID để có thứ tự ổn định."""
        return list(
            self.session.scalars(
                select(Region).order_by(
                    Region.region_name,
                    Region.id,
                )
            )
        )

    def get_by_id(self, region_id: str) -> Region | None:
        """Lấy một khu vực theo khóa chính để kiểm tra dữ liệu tham chiếu."""
        return self.session.get(Region, region_id)
