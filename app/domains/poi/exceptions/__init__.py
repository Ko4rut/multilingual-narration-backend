"""Các exception nghiệp vụ được công khai bởi domain POI."""

from app.domains.poi.exceptions.exceptions import (
    InvalidPoiFilter,
    InvalidPoiImage,
    InvalidAudioAsset,
    InvalidPoiQrCode,
    NarrationNotFound,
    PoiConflict,
    PoiNotFound,
    PoiReferenceNotFound,
    TtsGenerationFailed,
)

__all__ = [
    "InvalidPoiFilter",
    "InvalidPoiImage",
    "InvalidAudioAsset",
    "InvalidPoiQrCode",
    "NarrationNotFound",
    "PoiConflict",
    "PoiNotFound",
    "PoiReferenceNotFound",
    "TtsGenerationFailed",
]
