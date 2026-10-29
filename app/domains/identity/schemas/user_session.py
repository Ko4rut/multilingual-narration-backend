from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserSessionRead(BaseModel):
    # Model để đọc dữ liệu phiên người dùng từ cơ sở dữ liệu.
    # Không được sử dụng để tạo hoặc cập nhật phiên người dùng.
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None
