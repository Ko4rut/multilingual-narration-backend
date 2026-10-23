from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ListeningHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    installation_id: UUID
    poi_content_id: str
    poi_id: str
    trigger_type: str
    started_at: datetime
    completed_at: datetime | None
    duration_sec: int | None
    created_at: datetime
