from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domains.catalog.models.language import LanguageStatus
from app.domains.catalog.utils import (
    normalize_language_code,
    normalize_language_name,
)


class LanguageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    language_code: str
    language_name: str
    language_status: LanguageStatus


class LanguageCreate(BaseModel):
    language_code: str = Field(max_length=10)
    language_name: str = Field(max_length=100)
    language_status: LanguageStatus

    _normalize_code = field_validator("language_code")(normalize_language_code)
    _normalize_name = field_validator("language_name")(normalize_language_name)


class LanguageUpdate(BaseModel):
    language_name: str | None = Field(default=None, max_length=100)
    language_status: LanguageStatus | None = None

    @field_validator("language_name")
    @classmethod
    def validate_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("language_name must not be null")
        return normalize_language_name(value)

    @field_validator("language_status")
    @classmethod
    def validate_status(
        cls,
        value: LanguageStatus | None,
    ) -> LanguageStatus:
        if value is None:
            raise ValueError("language_status must not be null")
        return value

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self
