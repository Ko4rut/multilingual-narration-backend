from typing import Literal

from pydantic import BaseModel, Field, SecretStr

from app.domains.identity.schemas.manager_user import ManagerUserRead


class LoginRequest(BaseModel):
    """Thông tin xác thực được nhận tại API đăng nhập."""

    email: str = Field(min_length=3, max_length=255)
    password: SecretStr = Field(min_length=1, max_length=1024)


class AccessTokenResponse(BaseModel):
    """Access Token trả trong body; Refresh Token chỉ được đặt trong cookie."""

    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(gt=0)


class LoginResponse(AccessTokenResponse):
    """Kết quả đăng nhập gồm Access Token và thông tin người dùng an toàn."""

    user: ManagerUserRead
