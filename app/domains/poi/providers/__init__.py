"""Các provider hạ tầng được nghiệp vụ POI sử dụng."""

from app.domains.poi.providers.image_checksum import RemoteImageChecksumProvider
from app.domains.poi.providers.audio_asset import RemoteAudioAssetProvider, VerifiedAudioAsset
from app.domains.poi.providers.qr_code import (
    create_poi_qr_payload,
    parse_poi_qr_payload,
    render_qr_png,
)
from app.domains.poi.providers.tts import (
    FileSystemTtsStorage,
    GeneratedTtsAudio,
    GttsSynthesizer,
    StoredTtsAudio,
)

__all__ = [
    "FileSystemTtsStorage",
    "GeneratedTtsAudio",
    "GttsSynthesizer",
    "RemoteAudioAssetProvider",
    "RemoteImageChecksumProvider",
    "StoredTtsAudio",
    "VerifiedAudioAsset",
    "create_poi_qr_payload",
    "parse_poi_qr_payload",
    "render_qr_png",
]
