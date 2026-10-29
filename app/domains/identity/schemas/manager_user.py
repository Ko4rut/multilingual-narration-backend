from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from app.domains.identity.models.manager_user import ManagerUserStatus


class ManagerUserRead(BaseModel):
    # Model để đọc dữ liệu người dùng quản lý từ cơ sở dữ liệu. 
    # Không được sử dụng để tạo hoặc cập nhật người dùng quản lý.
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
    # Model để tạo người dùng quản lý mới. 
    # Sử dụng để nhận dữ liệu từ yêu cầu API và xác thực dữ liệu đó trước khi lưu vào cơ sở dữ liệu.
    role_id: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: SecretStr = Field(min_length=1, max_length=1024)
    full_name: str = Field(min_length=1, max_length=200)
    user_status: ManagerUserStatus = ManagerUserStatus.ACTIVE


class ManagerUserUpdate(BaseModel):
    # Model để cập nhật thông tin người dùng quản lý. 
    # Sử dụng để nhận dữ liệu từ yêu cầu API và xác thực dữ liệu đó trước khi cập nhật vào cơ sở dữ liệu.
    role_id: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    user_status: ManagerUserStatus | None = None
    password: SecretStr | None = Field(default=None, min_length=1, max_length=1024)

    @model_validator(mode="after") #
    def require_change(self) -> "ManagerUserUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self
