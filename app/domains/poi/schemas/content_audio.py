from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator


class ContentAudioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    poi_content_id: str
    audio_url: str
    audio_size: int
    audio_source_type: str
    audio_duration_sec: int
    audio_mime_type: str
    audio_checksum_sha256: str
    created_at: datetime
    last_updated_at: datetime


AudioSource = Literal["RECORD", "TTS"]
class AudioMetadataWrite(BaseModel):
    """Asset reference; backend derives and verifies all stored metadata."""
    model_config = ConfigDict(extra="forbid")

    audio_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    audio_source_type: AudioSource

    @field_validator("audio_url")
    @classmethod
    def validate_asset_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("audio_url must be an HTTP(S) asset URL without credentials")
        return value

class AdminContentAudioRead(ContentAudioRead):
    audio_source_type: AudioSource

    @field_validator("audio_source_type", mode="before")
    @classmethod
    def normalize_source(cls, value: str) -> str:
        return value.upper()


class ContentAudioPage(BaseModel):
    items: list[AdminContentAudioRead]
    total: int
    offset: int
    limit: int
