from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PoiContentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    poi_id: str
    language_id: str
    narration_title: str
    narration_script: str
    content_version: int
    content_status: str
    created_by: str
    approved_by: str | None
    published_by: str | None
    created_at: datetime
    approved_at: datetime | None
    published_at: datetime | None
