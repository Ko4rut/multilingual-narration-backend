from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.domains.poi.exceptions import InvalidPoiQrCode, PoiNotFound
from app.domains.poi.services.poi_content import PoiContentService


POI_ID = "poi-111126-12345678"


class PoiRepositoryStub:
    def __init__(self, *, active: bool = True):
        now = datetime.now(timezone.utc)
        self.poi = SimpleNamespace(
            id=POI_ID,
            region_id="region-12345678",
            poi_name="Museum",
            poi_image_url="https://assets.example/museum.webp",
            image_checksum_sha256="a" * 64,
            poi_qr_code=f"mnr://pois/{POI_ID}",
            poi_location="City centre",
            poi_status="ACTIVE" if active else "INACTIVE",
            latitude=Decimal("10.000000"),
            longitude=Decimal("106.000000"),
            trigger_radius_meter=Decimal("50.00"),
            created_at=now,
            last_updated_at=now,
        )

    def get_by_id(self, poi_id: str, *, active_only: bool = False):
        if poi_id != self.poi.id:
            return None
        if active_only and self.poi.poi_status != "ACTIVE":
            return None
        return self.poi


class ContentRepositoryStub:
    content = SimpleNamespace(
        id="cont-111126-12345678",
        poi_id=POI_ID,
        narration_title="English title",
        narration_script="English narration",
        content_version=1,
    )

    def get_published_for_language(self, poi_id: str, language_code: str):
        if poi_id == POI_ID and language_code == "en":
            return [self.content]
        return []


class AudioRepositoryStub:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.audio = SimpleNamespace(
            id="audio-111126-12345678",
            poi_content_id=ContentRepositoryStub.content.id,
            audio_url="https://assets.example/narration.mp3",
            audio_size=1024,
            audio_source_type="TTS",
            audio_duration_sec=30,
            audio_mime_type="audio/mpeg",
            audio_checksum_sha256="b" * 64,
            created_at=now,
            last_updated_at=now,
        )

    def get_content_ids_with_valid_audio(self, content_ids: list[str]):
        if self.audio.poi_content_id in content_ids:
            return {self.audio.poi_content_id}
        return set()

    def get_for_contents(self, content_ids: list[str]):
        if self.audio.poi_content_id in content_ids:
            return {self.audio.poi_content_id: self.audio}
        return {}


def build_service(*, active: bool = True) -> PoiContentService:
    return PoiContentService(
        session=SimpleNamespace(),
        pois=PoiRepositoryStub(active=active),
        contents=ContentRepositoryStub(),
        audios=AudioRepositoryStub(),
    )


def test_resolve_qr_returns_active_poi_and_english_fallback() -> None:
    result = build_service().resolve_qr(f"mnr://pois/{POI_ID}", "vi")

    assert result.poi.id == POI_ID
    assert result.narration.language_code == "en"
    assert result.narration.requested_language_code == "vi"
    assert result.narration.is_fallback is True
    assert result.narration.audio.audio_source_type == "TTS"


def test_resolve_qr_rejects_unknown_payload() -> None:
    with pytest.raises(InvalidPoiQrCode, match="Invalid POI QR code"):
        build_service().resolve_qr("https://example.com/not-an-mnr-qr", "en")


def test_resolve_qr_hides_inactive_poi() -> None:
    with pytest.raises(PoiNotFound, match="POI not found"):
        build_service(active=False).resolve_qr(f"mnr://pois/{POI_ID}", "en")
