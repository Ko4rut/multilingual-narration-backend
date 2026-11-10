from contextlib import contextmanager

from fastapi import HTTPException

from app.domains.poi.exceptions import (
    InvalidPoiFilter, NarrationNotFound, PoiConflict, PoiNotFound,
    PoiPermissionDenied, PoiReferenceNotFound,
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
    except InvalidPoiFilter as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PoiPermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TtsGenerationFailed as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
