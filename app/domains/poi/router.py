from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from app.domains.poi.repository import PoiRepository
from app.domains.poi.schemas import PoiRead
from app.domains.poi.service import PoiService
from app.route.dependencies import get_session

router = APIRouter(prefix="/pois", tags=["POI"])

def get_poi_service(session: Annotated[Session, Depends(get_session)]) -> PoiService:
    return PoiService(PoiRepository(session))

@router.get("", response_model=list[PoiRead])
def list_pois(service: Annotated[PoiService, Depends(get_poi_service)],
              offset: Annotated[int, Query(ge=0)] = 0,
              limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return service.list_pois(offset=offset, limit=limit)

@router.get("/{poi_id}", response_model=PoiRead)
def get_poi(poi_id: Annotated[int, Path(gt=0)],
            service: Annotated[PoiService, Depends(get_poi_service)]):
    return service.get_poi(poi_id)
