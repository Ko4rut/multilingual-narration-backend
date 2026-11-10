from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.domains.catalog.schemas.language import LanguageRead
from app.domains.poi.schemas.content_audio import AdminContentAudioRead


class PoiContentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    poi_id: str
    language_id: str
    narration_title: str
    narration_script: str
    content_version: int
    content_status: str
    created_by: str
    approved_by: str | None
    published_by: str | None
    created_at: datetime
    approved_at: datetime | None
    published_at: datetime | None


ContentStatus = Literal["DRAFT", "WAITING_APPROVAL", "REJECTED", "APPROVED", "PUBLISHED", "ARCHIVED"]
ContentIdentifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
NarrationTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
NarrationScript = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100_000)]


class PoiContentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    poi_id: ContentIdentifier
    language_id: ContentIdentifier
    narration_title: NarrationTitle
    narration_script: NarrationScript


class PoiContentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    narration_title: NarrationTitle | None = None
    narration_script: NarrationScript | None = None

    @model_validator(mode="after")
    def require_changes(self) -> "PoiContentUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Narration fields must not be null")
        return self


class PoiContentReview(BaseModel):
    """Quyết định của người kiểm duyệt đối với content đang chờ duyệt."""

    model_config = ConfigDict(extra="forbid")
    decision: Literal["APPROVE", "REJECT"]


class AdminPoiContentRead(PoiContentRead):
    content_status: ContentStatus
    audio: AdminContentAudioRead | None = None

    @field_validator("content_status", mode="before")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.upper()


class PoiContentPage(BaseModel):
    items: list[AdminPoiContentRead]
    total: int
    offset: int
    limit: int


class ContentPoiOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    poi_name: str


class PoiContentOptions(BaseModel):
    pois: list[ContentPoiOption]
    languages: list[LanguageRead]


class PublishedNarration(BaseModel):
    poi_id: str
    content_id: str
    language_code: str
    requested_language_code: str
    is_fallback: bool
    narration_title: str
    narration_script: str
    content_version: int
    audio: AdminContentAudioRead
