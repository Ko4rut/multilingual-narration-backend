from functools import lru_cache
from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8", extra="ignore",
    )
    app_name: str = "Multilingual Narration API"
    database_url: SecretStr = SecretStr("postgresql+psycopg://narration_app:narration_dev_password@localhost:5433/narration_db")

@lru_cache
def get_settings() -> Settings:
    return Settings()
