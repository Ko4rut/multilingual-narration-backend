from app.core.exceptions import ResourceNotFound
from app.domains.poi.models import PointOfInterest
from app.domains.poi.repository import PoiRepository

class PoiService:
    def __init__(self, repository: PoiRepository):
        self.repository = repository

    def list_pois(self, *, offset: int, limit: int) -> list[PointOfInterest]:
        return self.repository.list_active(offset=offset, limit=limit)

    def get_poi(self, poi_id: int) -> PointOfInterest:
        poi = self.repository.get_active(poi_id)
        if poi is None:
            raise ResourceNotFound("POI not found")
        return poi
