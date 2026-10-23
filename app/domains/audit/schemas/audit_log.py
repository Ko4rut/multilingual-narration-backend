from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    action: str
    entity_type: str
    entity_id: str
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    created_at: datetime
