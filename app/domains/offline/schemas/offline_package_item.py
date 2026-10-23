from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OfflinePackageItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    package_id: str
    poi_id: str
    poi_content_id: str
    audio_id: str
    content_version: int
    created_at: datetime
    last_updated_at: datetime
