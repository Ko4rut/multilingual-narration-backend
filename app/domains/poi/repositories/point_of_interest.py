from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.poi.models.point_of_interest import PointOfInterest


class PoiRepository:
    """Queries supporting the already implemented public POI endpoints."""

    def __init__(self, session: Session):
        self.session = session

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
