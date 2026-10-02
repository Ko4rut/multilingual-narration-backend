from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class PoiRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    region_id: int
    poi_name: str
    image_url: str | None
    qr_code: str
    poi_priority: int
    latitude: Decimal
    longitude: Decimal
    trigger_radius: Decimal
    poi_location: str
    is_active: bool
