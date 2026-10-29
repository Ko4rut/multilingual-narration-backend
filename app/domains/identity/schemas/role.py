from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PermissionId = Annotated[str, Field(min_length=1, max_length=50)]


class RoleRead(BaseModel):
    # Model để đọc dữ liệu vai trò từ cơ sở dữ liệu.
    # Không được sử dụng để tạo hoặc cập nhật vai trò.
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    created_by: str | None
    last_updated_by: str | None
    created_at: datetime
    last_updated_at: datetime | None


class RoleCreate(BaseModel):
    # Model để tạo vai trò mới.
    # Sử dụng để nhận dữ liệu từ yêu cầu API và xác thực dữ liệu đó trước khi lưu vào cơ sở dữ liệu.
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    permission_ids: list[PermissionId] = Field(default_factory=list, max_length=100)

    @field_validator("permission_ids")
    @classmethod
    def unique_permissions(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("permission_ids must not contain duplicates")
        return value


class RoleUpdate(BaseModel):
    # Model để cập nhật vai trò.
    # Sử dụng để nhận dữ liệu từ yêu cầu API và xác thực dữ liệu đó trước khi cập nhật vào cơ sở dữ liệu.
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None

    @model_validator(mode="after")
    def require_change(self) -> "RoleUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self


class RolePermissionsUpdate(BaseModel):
    # Model để cập nhật quyền của vai trò.
    # Sử dụng để nhận dữ liệu từ yêu cầu API và xác thực dữ liệu đó trước khi cập nhật vào cơ sở dữ liệu.
    permission_ids: list[PermissionId] = Field(max_length=100)

    @field_validator("permission_ids")
    @classmethod
    def unique_permissions(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("permission_ids must not contain duplicates")
        return value
