from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domains.catalog.models.region import Region
from app.domains.listening.models.listening_history import ListeningHistory
from app.domains.offline.models.offline_package_item import OfflinePackageItem
from app.domains.poi.models.poi_category_mapping import PoiCategoryMapping
from app.domains.poi.models.point_of_interest import PointOfInterest
from app.domains.poi.utils import escape_like_value


class PoiRepository:
    """Queries for public POI reads and administrative POI operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_choices(self) -> list[PointOfInterest]:
        return list(self.session.scalars(select(PointOfInterest).order_by(PointOfInterest.poi_name, PointOfInterest.id)))

    def list_active(self, *, offset: int, limit: int) -> list[PointOfInterest]:
        query = (
            select(PointOfInterest)
            .where(PointOfInterest.poi_status == "active")
            .order_by(PointOfInterest.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(query))

    def get_active(self, poi_id: str) -> PointOfInterest | None:
        return self.session.scalar(
            select(PointOfInterest).where(
                PointOfInterest.id == poi_id,
                PointOfInterest.poi_status == "active",
            )
        )

    def get_by_id(self, poi_id: str, *, for_update: bool = False) -> PointOfInterest | None:
        statement = select(PointOfInterest).where(PointOfInterest.id == poi_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def get_page(
        self, *, offset: int, limit: int, search: str | None,
        poi_status: str | None, region_id: str | None, category_id: str | None,
    ) -> tuple[list[PointOfInterest], int]:
        filters = []
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
        if poi_status == "ACTIVE":
            filters.append(PointOfInterest.poi_status == "active")
        elif poi_status == "INACTIVE":
            filters.append(PointOfInterest.poi_status != "active")
        if region_id is not None:
            filters.append(PointOfInterest.region_id == region_id)
        if category_id is not None:
            filters.append(select(PoiCategoryMapping.poi_id).where(
                PoiCategoryMapping.poi_id == PointOfInterest.id,
                PoiCategoryMapping.poi_category_id == category_id,
            ).exists())
        total = self.session.scalar(select(func.count()).select_from(PointOfInterest).where(*filters))
        items = list(self.session.scalars(
            select(PointOfInterest).where(*filters)
            .order_by(PointOfInterest.created_at.desc(), PointOfInterest.id)
            .offset(offset).limit(limit)
        ))
        return items, total

    def get_regions(self) -> list[Region]:
        return list(self.session.scalars(select(Region).order_by(Region.region_name, Region.id)))

    def region_exists(self, region_id: str) -> bool:
        return self.session.get(Region, region_id) is not None

    def has_duplicate(self, field: str, value: str, *, exclude_id: str | None = None) -> bool:
        columns = {
            "poi_qr_code": PointOfInterest.poi_qr_code,
            "poi_location": PointOfInterest.poi_location,
        }
        statement = select(PointOfInterest.id).where(columns[field] == value)
        if exclude_id is not None:
            statement = statement.where(PointOfInterest.id != exclude_id)
        return self.session.scalar(statement.limit(1)) is not None

    def has_external_references(self, poi_id: str) -> bool:
        for model in (ListeningHistory, OfflinePackageItem):
            if self.session.scalar(select(model.id).where(model.poi_id == poi_id).limit(1)) is not None:
                return True
        return False

    def add(self, poi: PointOfInterest) -> None:
        self.session.add(poi)

    def delete(self, poi: PointOfInterest) -> None:
        self.session.delete(poi)
