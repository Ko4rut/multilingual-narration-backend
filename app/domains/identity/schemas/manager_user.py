from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from app.domains.identity.models.manager_user import ManagerUserStatus


def validate_password_without_whitespace(
    password: SecretStr,
) -> SecretStr:
    """Từ chối mọi loại khoảng trắng nhưng không làm lộ giá trị mật khẩu."""

    if any(
        character.isspace() for character in password.get_secret_value()
    ):
        raise ValueError("password must not contain whitespace")
    return password


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

    @field_validator("password")
    @classmethod
    def reject_password_whitespace(cls, password: SecretStr) -> SecretStr:
        return validate_password_without_whitespace(password)


class ManagerUserUpdate(BaseModel):
    # Model để cập nhật thông tin người dùng quản lý. 
    # Sử dụng để nhận dữ liệu từ yêu cầu API và xác thực dữ liệu đó trước khi cập nhật vào cơ sở dữ liệu.
    role_id: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    user_status: ManagerUserStatus | None = None
    password: SecretStr | None = Field(default=None, min_length=1, max_length=1024)

    @field_validator("password")
    @classmethod
    def reject_password_whitespace(
        cls,
        password: SecretStr | None,
    ) -> SecretStr | None:
        if password is None:
            return None
        return validate_password_without_whitespace(password)

    @model_validator(mode="after")
    def require_change(self) -> "ManagerUserUpdate":
        # Bắt buộc có ít nhất một field được gửi lên (không chấp nhận body rỗng).
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self
