from io import BytesIO

import pytest

from app.domains.poi.exceptions import InvalidPoiImage
from app.domains.poi.providers.poi_image import FileSystemPoiImageStorage


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"image-content"


def test_store_poi_image_uses_checksum_filename(tmp_path) -> None:
    storage = FileSystemPoiImageStorage(
        tmp_path, "http://localhost:8000/api/v1/assets/images/pois",
    )

    stored = storage.save(BytesIO(PNG_BYTES), "image/png")

    assert stored.url.endswith(f"/{stored.checksum_sha256}.png")
    assert stored.size == len(PNG_BYTES)
    assert storage.get_path(f"{stored.checksum_sha256}.png") is not None
    assert storage.get_checksum(stored.url) == stored.checksum_sha256


def test_store_poi_image_rejects_mismatched_content(tmp_path) -> None:
    storage = FileSystemPoiImageStorage(tmp_path, "https://assets.example/pois")

    with pytest.raises(InvalidPoiImage, match="does not match"):
        storage.save(BytesIO(b"not-a-png"), "image/png")


def test_store_poi_image_rejects_unsupported_mime(tmp_path) -> None:
    storage = FileSystemPoiImageStorage(tmp_path, "https://assets.example/pois")

    with pytest.raises(InvalidPoiImage, match="JPEG, PNG or WebP"):
        storage.save(BytesIO(b"gif"), "image/gif")
