"""Lưu và phục vụ ảnh POI được tải trực tiếp lên hệ thống."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO
import os
import re

from app.domains.poi.exceptions import InvalidPoiImage


MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_TYPES = {
    "image/jpeg": ("jpg", lambda value: value.startswith(b"\xff\xd8\xff")),
    "image/png": ("png", lambda value: value.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (
        "webp",
        lambda value: len(value) >= 12
        and value.startswith(b"RIFF")
        and value[8:12] == b"WEBP",
    ),
}
IMAGE_FILENAME_PATTERN = re.compile(r"^[0-9a-f]{64}\.(?:jpg|png|webp)$")


@dataclass(frozen=True)
class StoredPoiImage:
    url: str
    checksum_sha256: str
    size: int
    mime_type: str


class FileSystemPoiImageStorage:
    """Lưu ảnh theo checksum để tên file ổn định và tự loại bỏ file trùng."""

    def __init__(self, directory: Path, public_base_url: str) -> None:
        self.directory = directory
        self.public_base_url = public_base_url.rstrip("/")

    def save(self, source: BinaryIO, content_type: str | None) -> StoredPoiImage:
        mime_type = (content_type or "").lower().split(";", 1)[0]
        image_type = IMAGE_TYPES.get(mime_type)
        if image_type is None:
            raise InvalidPoiImage("POI image must be JPEG, PNG or WebP")
        extension, has_valid_signature = image_type
        self.directory.mkdir(parents=True, exist_ok=True)
        digest = sha256()
        size = 0
        header = b""
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(dir=self.directory, delete=False) as temporary:
                temporary_path = Path(temporary.name)
                while chunk := source.read(64 * 1024):
                    size += len(chunk)
                    if size > MAX_IMAGE_BYTES:
                        raise InvalidPoiImage("POI image exceeds the 10 MiB limit")
                    if len(header) < 16:
                        header = (header + chunk)[:16]
                    digest.update(chunk)
                    temporary.write(chunk)
            if size == 0:
                raise InvalidPoiImage("POI image must not be empty")
            if not has_valid_signature(header):
                raise InvalidPoiImage("POI image content does not match its MIME type")
            checksum = digest.hexdigest()
            filename = f"{checksum}.{extension}"
            destination = self.directory / filename
            if destination.exists():
                temporary_path.unlink(missing_ok=True)
            else:
                os.replace(temporary_path, destination)
            return StoredPoiImage(
                url=f"{self.public_base_url}/{filename}",
                checksum_sha256=checksum,
                size=size,
                mime_type=mime_type,
            )
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

    def get_path(self, filename: str) -> Path | None:
        if IMAGE_FILENAME_PATTERN.fullmatch(filename) is None:
            return None
        path = self.directory / filename
        return path if path.is_file() else None

    def get_checksum(self, url: str) -> str | None:
        prefix = f"{self.public_base_url}/"
        if not url.startswith(prefix):
            return None
        filename = url.removeprefix(prefix)
        if IMAGE_FILENAME_PATTERN.fullmatch(filename) is None:
            raise InvalidPoiImage("Invalid managed POI image URL")
        if not (self.directory / filename).is_file():
            raise InvalidPoiImage("Uploaded POI image was not found")
        return filename.split(".", 1)[0]
