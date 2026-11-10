from app.core.exceptions import ResourceNotFound
from app.domains.poi.models.point_of_interest import PointOfInterest
from app.domains.poi.repositories.point_of_interest import PoiRepository
from app.domains.poi.schemas.point_of_interest import PoiPage


class PoiService:
    def __init__(self, repository: PoiRepository):
        self.repository = repository

    def list_pois(self, *, offset: int, limit: int) -> PoiPage:
        items = self.repository.get_all(
            offset=offset,
            limit=limit,
            poi_status="ACTIVE",
            sort_by="id",
        )
        total = self.repository.get_count(poi_status="ACTIVE")
        return PoiPage(items=items, total=total, offset=offset, limit=limit)

    def get_poi(self, poi_id: str) -> PointOfInterest:
        poi = self.repository.get_by_id(poi_id, active_only=True)
        if poi is None:
            raise ResourceNotFound("POI not found")
        return poi
