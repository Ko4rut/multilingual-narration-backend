from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PoiRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    region_id: int
    poi_name: str
    poi_image_url: str | None
    image_checksum_sha256: str | None
    poi_qr_code: str
    poi_location: str
    poi_status: str
    latitude: Decimal
    longitude: Decimal
    trigger_radius_meter: Decimal
    created_at: datetime
    last_updated_at: datetime
