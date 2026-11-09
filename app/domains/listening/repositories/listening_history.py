from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.listening.models.listening_history import ListeningHistory
from app.domains.poi.models.poi_content import PoiContent
from app.domains.poi.models.point_of_interest import PointOfInterest


class ListeningHistoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(
        self, event_id: str, *, for_update: bool = False
    ) -> ListeningHistory | None:
        statement = select(ListeningHistory).where(ListeningHistory.id == event_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return self.session.scalar(statement)

    def poi_exists(self, poi_id: str) -> bool:
        statement = select(PointOfInterest.id).where(
            PointOfInterest.id == poi_id
        )
        return self.session.scalar(statement) is not None

    def get_content(self, content_id: str) -> PoiContent | None:
        return self.session.scalar(
            select(PoiContent).where(PoiContent.id == content_id)
        )

    def add(self, event: ListeningHistory) -> None:
        self.session.add(event)
