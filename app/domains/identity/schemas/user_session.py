from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserSessionRead(BaseModel):
    """Public session fields; the refresh-token hash is intentionally excluded."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None
