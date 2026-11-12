from contextlib import contextmanager

from fastapi import HTTPException

from app.domains.poi.exceptions import (
    InvalidAudioAsset, InvalidPoiFilter, InvalidPoiImage, InvalidPoiQrCode,
    NarrationNotFound, PoiConflict, PoiNotFound, PoiReferenceNotFound,
    TtsGenerationFailed,
)


@contextmanager
def poi_http_errors():
    """Translate domain errors at the POI HTTP boundary only."""
    try:
        yield
    except (PoiNotFound, PoiReferenceNotFound, NarrationNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PoiConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (InvalidAudioAsset, InvalidPoiFilter, InvalidPoiImage, InvalidPoiQrCode) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TtsGenerationFailed as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
