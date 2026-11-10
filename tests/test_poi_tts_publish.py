from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace

from app.domains.poi.models.poi_content import PoiContent
from app.domains.poi.services.poi_content import PoiContentService
from app.domains.poi.tts import GeneratedTtsAudio, StoredTtsAudio
from app.domains.poi.tts import FileSystemTtsStorage


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

    def get_language(self, language_id: str):
        return SimpleNamespace(language_status="SUPPORTED", language_code="vi")

    def get_published_versions(self, poi_id: str, language_id: str):
        return []


class AudioRepositoryStub:
    def __init__(self):
        self.audio = None

    def get_content_ids_with_valid_audio(self, content_ids: list[str]):
        return {self.audio.poi_content_id} if self.audio is not None else set()

    def get_for_content(self, content_id: str, *, for_update: bool = False):
        return self.audio

    def get_for_contents(self, content_ids: list[str]):
        return {self.audio.poi_content_id: self.audio} if self.audio is not None else {}

    def add(self, audio) -> None:
        self.audio = audio


class TtsStub:
    def __init__(self):
        self.calls = []

    def synthesize(self, text: str, language_code: str):
        self.calls.append((text, language_code))
        return GeneratedTtsAudio(data=b"mp3-data", duration_sec=3)


class StorageStub:
    def store(self, audio: GeneratedTtsAudio):
        return StoredTtsAudio(
            url="http://localhost:8000/api/v1/assets/audio/" + "a" * 64 + ".mp3",
            size=len(audio.data),
            duration_sec=audio.duration_sec,
            checksum_sha256="a" * 64,
        )


def test_publish_generates_and_registers_tts_when_audio_is_missing() -> None:
    now = datetime.now(timezone.utc)
    content = PoiContent(
        id="cont-010126-12345678",
        poi_id="poi-010126-12345678",
        language_id="lang-12345678",
        narration_title="Xin chào",
        narration_script="Nội dung tiếng Việt",
        content_version=1,
        content_status="APPROVED",
        created_by="user-author",
        approved_by="user-reviewer",
        published_by=None,
        created_at=now,
        approved_at=now,
        published_at=None,
    )
    audios = AudioRepositoryStub()
    tts = TtsStub()
    service = PoiContentService(
        SessionStub(), PoiRepositoryStub(), ContentRepositoryStub(content), audios,
        tts=tts, tts_storage=StorageStub(),
    )

    result = service.publish_content(content.id, actor_id="user-publisher")

    assert tts.calls == [("Xin chào. Nội dung tiếng Việt", "vi")]
    assert result.content_status == "PUBLISHED"
    assert result.audio is not None
    assert result.audio.audio_source_type == "TTS"
    assert content.published_by == "user-publisher"


def test_tts_storage_uses_immutable_checksum_path(tmp_path) -> None:
    storage = FileSystemTtsStorage(
        tmp_path, "http://localhost:8000/api/v1/assets/audio/",
    )

    stored = storage.store(GeneratedTtsAudio(data=b"audio-bytes", duration_sec=2))

    assert stored.url.endswith(f"/{stored.checksum_sha256}.mp3")
    assert stored.size == len(b"audio-bytes")
    assert storage.get_path(stored.checksum_sha256).read_bytes() == b"audio-bytes"
