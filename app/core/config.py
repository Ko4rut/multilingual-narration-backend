from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Multilingual Narration API"
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://narration_app:"
        "narration_dev_password@localhost:5433/narration_db"
    )

    # Khóa JWT không có giá trị mặc định để tránh vô tình chạy với khóa mẫu.
    jwt_private_key: SecretStr | None = None
    jwt_public_keys: dict[str, str] = Field(default_factory=dict)
    jwt_active_key_id: str = "auth-key-1"
    jwt_issuer: str = "mnr-backend"
    jwt_audience: str = "mnr-admin-web"
    jwt_leeway_seconds: int = Field(default=30, ge=0)
    access_token_ttl_seconds: int = Field(default=900, gt=0)
    refresh_token_ttl_seconds: int = Field(default=2_592_000, gt=0)

    auth_refresh_cookie_name: str = "refresh_token"
    auth_cookie_path: str = "/api/v1/identity"
    auth_cookie_domain: str | None = None
    auth_cookie_secure: bool = True
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "strict"


@lru_cache
def get_settings() -> Settings:
    return Settings()
