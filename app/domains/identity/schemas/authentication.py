from typing import Literal

from pydantic import BaseModel, Field, SecretStr

from app.domains.identity.schemas.manager_user import ManagerUserRead


class LoginRequest(BaseModel):
    """Dữ liệu yêu cầu đăng nhập của người dùng quản lý."""

    email: str = Field(min_length=3, max_length=255)
    password: SecretStr = Field(min_length=1, max_length=1024)


class AccessTokenResponse(BaseModel):
    """Access Token được cấp cho người dùng quản lý sau khi đăng nhập thành công."""

    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(gt=0)


class LoginResponse(AccessTokenResponse):
    """Access Token và thông tin công khai của tài khoản đã đăng nhập."""

    user: ManagerUserRead
