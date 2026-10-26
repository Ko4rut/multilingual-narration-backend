from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.identity.enums import ManagerUserStatus


class ManagerUserRead(BaseModel):
    """Public manager-user fields; the password hash is intentionally excluded."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    role_id: str
    email: str
    full_name: str
    user_status: ManagerUserStatus
    created_at: datetime
    last_updated_at: datetime
    last_login_at: datetime | None
