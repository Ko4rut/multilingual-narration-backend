from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
