from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domains.poi.models import PointOfInterest

class PoiRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_active(self, *, offset: int, limit: int) -> list[PointOfInterest]:
        query = (select(PointOfInterest).where(PointOfInterest.is_active.is_(True))
                 .order_by(PointOfInterest.id).offset(offset).limit(limit))
        return list(self.session.scalars(query))

    def get_active(self, poi_id: int) -> PointOfInterest | None:
        return self.session.scalar(select(PointOfInterest).where(
            PointOfInterest.id == poi_id, PointOfInterest.is_active.is_(True)))
