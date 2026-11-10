from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.domains.poi.models.poi_category_mapping import PoiCategoryMapping
from app.domains.poi.models.point_of_interest import PointOfInterest
from app.domains.poi.utils import escape_like_value


class PoiRepository:
    """Truy vấn và thêm POI; repository không commit hoặc thực hiện hard delete."""

    def __init__(self, session: Session):
        self.session = session

    def get_all(
        self,
        *,
        offset: int | None = None,
        limit: int | None = None,
        search: str | None = None,
        poi_status: str | None = None,
        region_id: str | None = None,
        category_id: str | None = None,
        sort_by: Literal["id", "name", "created_at"] = "name",
    ) -> list[PointOfInterest]:
        """Lấy POI với phân trang, tìm kiếm và các bộ lọc tùy chọn."""
        filters = self._get_filters(
            search=search,
            poi_status=poi_status,
            region_id=region_id,
            category_id=category_id,
        )
        statement = select(PointOfInterest).where(*filters)
        if sort_by == "id":
            statement = statement.order_by(PointOfInterest.id)
        elif sort_by == "created_at":
            statement = statement.order_by(
                PointOfInterest.created_at.desc(),
                PointOfInterest.id,
            )
        else:
            statement = statement.order_by(
                PointOfInterest.poi_name,
                PointOfInterest.id,
            )
        if offset is not None:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.session.scalars(statement))

    def get_count(
        self,
        *,
        search: str | None = None,
        poi_status: str | None = None,
        region_id: str | None = None,
        category_id: str | None = None,
    ) -> int:
        """Đếm POI theo cùng bộ lọc của ``get_all`` để phục vụ phân trang."""
        filters = self._get_filters(
            search=search,
            poi_status=poi_status,
            region_id=region_id,
            category_id=category_id,
        )
        return self.session.scalar(
            select(func.count()).select_from(PointOfInterest).where(*filters)
        )

    def get_by_id(
        self,
        poi_id: str,
        *,
        active_only: bool = False,
        for_update: bool = False,
    ) -> PointOfInterest | None:
        """Lấy POI theo ID, có thể giới hạn POI ACTIVE hoặc khóa dòng khi ghi."""
        statement = select(PointOfInterest).where(PointOfInterest.id == poi_id)
        if active_only:
            statement = statement.where(func.upper(PointOfInterest.poi_status) == "ACTIVE")
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    @staticmethod
    def _get_filters(
        *,
        search: str | None,
        poi_status: str | None,
        region_id: str | None,
        category_id: str | None,
    ) -> list[ColumnElement[bool]]:
        """Tạo điều kiện dùng chung cho truy vấn danh sách và tổng số bản ghi."""
        filters: list[ColumnElement[bool]] = []
        if search is not None:
            escaped = escape_like_value(search)
            pattern = f"%{escaped}%"
            filters.append(or_(*[
                column.ilike(pattern, escape="\\")
                for column in (
                    PointOfInterest.id, PointOfInterest.poi_name,
                    PointOfInterest.poi_location, PointOfInterest.poi_qr_code,
                )
            ]))
        if poi_status is not None:
            filters.append(func.upper(PointOfInterest.poi_status) == poi_status)
        if region_id is not None:
            filters.append(PointOfInterest.region_id == region_id)
        if category_id is not None:
            filters.append(select(PoiCategoryMapping.poi_id).where(
                PoiCategoryMapping.poi_id == PointOfInterest.id,
                PoiCategoryMapping.poi_category_id == category_id,
            ).exists())
        return filters

    def add(self, poi: PointOfInterest) -> None:
        """Đưa POI mới vào Session; service chịu trách nhiệm transaction."""
        self.session.add(poi)
