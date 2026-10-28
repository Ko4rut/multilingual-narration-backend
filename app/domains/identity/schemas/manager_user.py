from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from app.domains.identity.models.manager_user import ManagerUserStatus


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


class ManagerUserCreate(BaseModel):
    role_id: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: SecretStr = Field(min_length=1, max_length=1024)
    full_name: str = Field(min_length=1, max_length=200)
    user_status: ManagerUserStatus = ManagerUserStatus.ACTIVE


class ManagerUserUpdate(BaseModel):
    role_id: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    user_status: ManagerUserStatus | None = None

    @model_validator(mode="after")
    def require_change(self) -> "ManagerUserUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self


class ManagerUserPasswordUpdate(BaseModel):
    password: SecretStr = Field(min_length=1, max_length=1024)
