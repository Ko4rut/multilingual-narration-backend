"""Các exception nghiệp vụ được công khai bởi domain POI."""

from app.domains.poi.exceptions.exceptions import (
    InvalidPoiFilter,
    NarrationNotFound,
    PoiConflict,
    PoiNotFound,
    PoiPermissionDenied,
    PoiReferenceNotFound,
    TtsGenerationFailed,
)

__all__ = [
    "InvalidPoiFilter",
    "NarrationNotFound",
    "PoiConflict",
    "PoiNotFound",
    "PoiPermissionDenied",
    "PoiReferenceNotFound",
    "TtsGenerationFailed",
]
