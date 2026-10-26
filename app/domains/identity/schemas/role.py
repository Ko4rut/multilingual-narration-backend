from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    created_by: str | None
    last_updated_by: str | None
    created_at: datetime
    last_updated_at: datetime | None
