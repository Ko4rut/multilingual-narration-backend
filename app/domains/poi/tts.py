"""Sinh và lưu audio TTS cho quy trình publish narration."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from math import ceil
from pathlib import Path
from tempfile import NamedTemporaryFile

from gtts import gTTS
from mutagen.mp3 import MP3

from app.domains.poi.exceptions import TtsGenerationFailed


@dataclass(frozen=True)
class GeneratedTtsAudio:
    data: bytes
    duration_sec: int


@dataclass(frozen=True)
class StoredTtsAudio:
    url: str
    size: int
    duration_sec: int
    checksum_sha256: str


class GttsSynthesizer:
    """Dùng gTTS để tạo MP3; lời gọi này cần kết nối mạng."""

    def synthesize(self, text: str, language_code: str) -> GeneratedTtsAudio:
        output = BytesIO()
        try:
            gTTS(text=text, lang=language_code, slow=False).write_to_fp(output)
            data = output.getvalue()
            duration = ceil(MP3(BytesIO(data)).info.length)
        except Exception as exc:
            raise TtsGenerationFailed("Unable to generate TTS audio") from exc
        if not data or duration <= 0:
            raise TtsGenerationFailed("TTS provider returned invalid audio")
        return GeneratedTtsAudio(data=data, duration_sec=duration)


class FileSystemTtsStorage:
    """Lưu MP3 bất biến theo checksum và trả URL công khai của asset."""

    def __init__(self, directory: Path, public_base_url: str):
        self.directory = directory
        self.public_base_url = public_base_url.rstrip("/")

    def store(self, audio: GeneratedTtsAudio) -> StoredTtsAudio:
        checksum = sha256(audio.data).hexdigest()
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            destination = self.directory / f"{checksum}.mp3"
            if not destination.exists():
                with NamedTemporaryFile(dir=self.directory, delete=False) as temporary:
                    temporary.write(audio.data)
                    temporary.flush()
                    temporary_path = Path(temporary.name)
                temporary_path.replace(destination)
        except OSError as exc:
            raise TtsGenerationFailed("Unable to store generated TTS audio") from exc
        return StoredTtsAudio(
            url=f"{self.public_base_url}/{checksum}.mp3",
            size=len(audio.data),
            duration_sec=audio.duration_sec,
            checksum_sha256=checksum,
        )

    def get_path(self, checksum: str) -> Path | None:
        path = self.directory / f"{checksum}.mp3"
        return path if path.is_file() else None
