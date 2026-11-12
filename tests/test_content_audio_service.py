from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.domains.poi.exceptions import PoiConflict
from app.domains.poi.models.content_audio import ContentAudio
from app.domains.poi.models.poi_content import PoiContent
from app.domains.poi.schemas.content_audio import AudioMetadataWrite
from app.domains.poi.services.content_audio import ContentAudioService


class SessionStub:
    def begin(self):
        return nullcontext()

    def flush(self) -> None:
        pass


class PoiRepositoryStub:
    poi = SimpleNamespace(id="poi-010126-12345678", poi_status="INACTIVE")

    def get_by_id(self, poi_id: str, *, for_update: bool = False):
        return self.poi


class ContentRepositoryStub:
    def __init__(self, content: PoiContent):
        self.content = content

    def get_by_id(self, content_id: str, *, for_update: bool = False):
        return self.content


class AudioRepositoryStub:
    def __init__(self, audio: ContentAudio):
        self.audio = audio

    def get_for_content(self, content_id: str, *, for_update: bool = False):
        return self.audio


def test_existing_audio_url_is_immutable() -> None:
    now = datetime.now(timezone.utc)
    content = PoiContent(
        id="cont-010126-12345678",
        poi_id="poi-010126-12345678",
        language_id="lang-12345678",
        narration_title="Title",
        narration_script="Script",
        content_version=1,
        content_status="APPROVED",
        created_by="user-author",
        created_at=now,
    )
    audio = ContentAudio(
        id="audio-010126-12345678",
        poi_content_id=content.id,
        audio_url="https://assets.example/original.mp3",
        audio_size=1024,
        audio_source_type="RECORD",
        audio_duration_sec=10,
        audio_mime_type="audio/mpeg",
        audio_checksum_sha256="a" * 64,
        created_at=now,
        last_updated_at=now,
    )
    service = ContentAudioService(
        SessionStub(),
        PoiRepositoryStub(),
        ContentRepositoryStub(content),
        AudioRepositoryStub(audio),
    )
    payload = AudioMetadataWrite(
        audio_url="https://assets.example/replacement.mp3",
        audio_size=audio.audio_size,
        audio_source_type="RECORD",
        audio_duration_sec=audio.audio_duration_sec,
        audio_mime_type=audio.audio_mime_type,
        audio_checksum_sha256=audio.audio_checksum_sha256,
    )

    with pytest.raises(PoiConflict, match="URL is immutable"):
        service.save_audio(content.id, payload)

    assert audio.audio_url == "https://assets.example/original.mp3"
