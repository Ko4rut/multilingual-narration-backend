from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.catalog.models.region import Region


class RegionRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> list[Region]:
        return list(
            self.session.scalars(select(Region).order_by(Region.id))
        )
