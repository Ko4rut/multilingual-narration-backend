from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.domains.identity.services.authentication import AuthenticatedIdentity
from app.domains.poi.repositories.point_of_interest import PoiRepository
from app.domains.poi.providers.qr_code import render_qr_png
from app.domains.poi.routers.dependencies import (
    get_content_audio_service, get_point_of_interest_service,
    get_tts_storage, require_poi_create,
    require_poi_read, require_poi_update,
    get_poi_content_service, require_narration_read, require_narration_create,
    require_narration_update, require_narration_approve,
    require_narration_publish,
)
from app.domains.poi.routers.http import poi_http_errors
from app.domains.poi.schemas.point_of_interest import (
    AdminPoiPage, AdminPoiRead, PoiCreate, PoiFormOptions, PoiRead,
    PoiPage, PoiStatus, PoiStatusUpdate, PoiUpdate,
)
from app.domains.poi.schemas.content_audio import (
    AdminContentAudioRead, AudioMetadataWrite, AudioSource, ContentAudioPage,
)
from app.domains.poi.schemas.poi_content import (
    AdminPoiContentRead, ContentStatus, PoiContentCreate, PoiContentOptions,
    PoiContentPage, PoiContentReview, PoiContentUpdate, PublishedNarration,
    QrNarrationRead, QrNarrationResolve,
)
from app.domains.poi.services import (
    ContentAudioService,
    PointOfInterestService,
    PublicPointOfInterestService,
    PoiContentService,
)
from app.domains.poi.providers.tts import FileSystemTtsStorage
from app.route.dependencies import get_session


router = APIRouter(prefix="/pois")
asset_router = APIRouter(prefix="/assets/audio", tags=["Content Audio (Public)"])


@asset_router.get(
    "/{checksum}.mp3",
    response_class=FileResponse,
    summary="Download generated narration audio",
)
def get_tts_audio(
    checksum: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
    storage: Annotated[FileSystemTtsStorage, Depends(get_tts_storage)],
) -> FileResponse:
    path = storage.get_path(checksum)
    if path is None:
        raise HTTPException(status_code=404, detail="Audio asset not found")
    return FileResponse(path, media_type="audio/mpeg", filename=f"{checksum}.mp3")


def get_public_point_of_interest_service(
    session: Annotated[Session, Depends(get_session)],
) -> PublicPointOfInterestService:
    return PublicPointOfInterestService(PoiRepository(session))


@router.get(
    "", response_model=PoiPage, summary="List active POIs",
    tags=["Point Of Interest (Public)"],
)
def list_pois(
    service: Annotated[
        PublicPointOfInterestService,
        Depends(get_public_point_of_interest_service),
    ],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PoiPage:
    return service.list_pois(offset=offset, limit=limit)


@router.get(
    "/{poi_id}", response_model=PoiRead, summary="Get an active POI",
    tags=["Point Of Interest (Public)"],
)
def get_poi(
    poi_id: Annotated[str, Path(min_length=1, max_length=50)],
    service: Annotated[
        PublicPointOfInterestService,
        Depends(get_public_point_of_interest_service),
    ],
):
    return service.get_poi(poi_id)


@router.post(
    "/qr/resolve",
    response_model=QrNarrationRead,
    summary="Resolve a POI QR code",
    tags=["Point Of Interest (Public)"],
)
def resolve_poi_qr(
    payload: QrNarrationResolve,
    service: Annotated[PoiContentService, Depends(get_poi_content_service)],
) -> QrNarrationRead:
    """Resolve a system QR to an active POI and playable online narration."""
    with poi_http_errors():
        return service.resolve_qr(payload.qr_code, payload.language_code)


admin_router = APIRouter(prefix="/admin/pois", tags=["Point Of Interest"])
Service = Annotated[
    PointOfInterestService,
    Depends(get_point_of_interest_service),
]
PoiId = Annotated[str, Path(min_length=1, max_length=50)]
ReadAccess = Annotated[AuthenticatedIdentity, Depends(require_poi_read)]
CreateAccess = Annotated[AuthenticatedIdentity, Depends(require_poi_create)]
UpdateAccess = Annotated[AuthenticatedIdentity, Depends(require_poi_update)]


@admin_router.get(
    "", response_model=AdminPoiPage,
    summary="List POIs", operation_id="list_pois_api_v1_admin_pois_get",
)
def list_admin_pois(
    identity: ReadAccess, service: Service,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    poi_status: PoiStatus | None = None,
    region_id: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    category_id: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
) -> AdminPoiPage:
    with poi_http_errors():
        return service.list_pois(
            offset=offset, limit=limit, search=search, poi_status=poi_status,
            region_id=region_id, category_id=category_id,
        )


@admin_router.get(
    "/options",
    response_model=PoiFormOptions,
    summary="Get POI form options",
)
def get_options(identity: ReadAccess, service: Service) -> PoiFormOptions:
    """Read region/category data for the existing POI form."""
    return service.get_options()


@admin_router.get(
    "/{poi_id}", response_model=AdminPoiRead,
    summary="Get a POI", operation_id="get_poi_api_v1_admin_pois__poi_id__get",
)
def get_admin_poi(poi_id: PoiId, identity: ReadAccess, service: Service) -> AdminPoiRead:
    with poi_http_errors():
        return service.get_poi(poi_id)


@admin_router.get(
    "/{poi_id}/qr-code",
    response_class=Response,
    summary="Get a POI QR code",
    responses={200: {"content": {"image/png": {}}}},
)
def get_poi_qr_code(
    poi_id: PoiId,
    identity: ReadAccess,
    service: Service,
) -> Response:
    """Tạo ảnh PNG từ payload QR đã được backend gán cho POI."""

    with poi_http_errors():
        poi = service.get_poi(poi_id)
        return Response(
            content=render_qr_png(poi.poi_qr_code),
            media_type="image/png",
            headers={
                "Content-Disposition": f'inline; filename="{poi.id}-qr.png"',
                "Cache-Control": "private, max-age=3600",
            },
        )


@admin_router.post(
    "", response_model=AdminPoiRead, status_code=201, summary="Create a POI"
)
def create_poi(payload: PoiCreate, identity: CreateAccess, service: Service) -> AdminPoiRead:
    with poi_http_errors():
        return service.create_poi(payload, actor_id=identity.manager_user.id)


@admin_router.patch(
    "/{poi_id}", response_model=AdminPoiRead, summary="Update a POI"
)
def update_poi(
    poi_id: PoiId, payload: PoiUpdate, identity: UpdateAccess, service: Service,
) -> AdminPoiRead:
    with poi_http_errors():
        return service.update_poi(poi_id, payload, actor_id=identity.manager_user.id)


@admin_router.patch(
    "/{poi_id}/status",
    response_model=AdminPoiRead,
    summary="Update POI status",
)
def update_status(
    poi_id: PoiId, payload: PoiStatusUpdate, identity: UpdateAccess, service: Service,
) -> AdminPoiRead:
    with poi_http_errors():
        return service.update_poi(
            poi_id, PoiUpdate(poi_status=payload.poi_status), actor_id=identity.manager_user.id,
        )


content_router = APIRouter(prefix="/admin/poi-contents", tags=["POI Content"])
audio_router = APIRouter(prefix="/admin/audios", tags=["Content Audio"])
ContentService = Annotated[PoiContentService, Depends(get_poi_content_service)]
AudioService = Annotated[ContentAudioService, Depends(get_content_audio_service)]
ContentId = Annotated[str, Path(min_length=1, max_length=50)]
FilterId = Annotated[str | None, Query(min_length=1, max_length=50)]
ContentReadAccess = Annotated[AuthenticatedIdentity, Depends(require_narration_read)]
ContentCreateAccess = Annotated[AuthenticatedIdentity, Depends(require_narration_create)]
ContentUpdateAccess = Annotated[AuthenticatedIdentity, Depends(require_narration_update)]
ContentApproveAccess = Annotated[AuthenticatedIdentity, Depends(require_narration_approve)]
ContentPublishAccess = Annotated[AuthenticatedIdentity, Depends(require_narration_publish)]


@content_router.get("", response_model=PoiContentPage, summary="List narration contents")
def list_contents(
    identity: ContentReadAccess, service: ContentService,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    poi_id: FilterId = None, language_id: FilterId = None,
    content_status: ContentStatus | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
) -> PoiContentPage:
    with poi_http_errors():
        return service.list_contents(
            offset=offset, limit=limit, poi_id=poi_id, language_id=language_id,
            content_status=content_status, search=search,
        )


@content_router.get(
    "/options",
    response_model=PoiContentOptions,
    summary="Get narration content form options",
)
def get_content_options(identity: ContentReadAccess, service: ContentService) -> PoiContentOptions:
    return service.get_options()


@content_router.get(
    "/{content_id}",
    response_model=AdminPoiContentRead,
    summary="Get narration content",
)
def get_content(content_id: ContentId, identity: ContentReadAccess, service: ContentService) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.get_content(content_id)


@content_router.post(
    "",
    response_model=AdminPoiContentRead,
    status_code=201,
    summary="Create narration content",
)
def create_content(
    payload: PoiContentCreate, identity: ContentCreateAccess, service: ContentService,
) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.create_content(payload, actor_id=identity.manager_user.id)


@content_router.patch(
    "/{content_id}",
    response_model=AdminPoiContentRead,
    summary="Update narration content",
)
def update_content(
    content_id: ContentId, payload: PoiContentUpdate,
    identity: ContentUpdateAccess, service: ContentService,
) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.update_content(content_id, payload)


@content_router.post(
    "/{content_id}/submit",
    response_model=AdminPoiContentRead,
    summary="Submit narration content for review",
)
def submit_content(content_id: ContentId, identity: ContentUpdateAccess, service: ContentService) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.submit_content(content_id)


@content_router.post(
    "/{content_id}/review",
    response_model=AdminPoiContentRead,
    summary="Review narration content",
)
def review_content(
    content_id: ContentId, payload: PoiContentReview,
    identity: ContentApproveAccess, service: ContentService,
) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.review_content(
            content_id, payload, actor_id=identity.manager_user.id,
        )


@content_router.post(
    "/{content_id}/publish",
    response_model=AdminPoiContentRead,
    summary="Publish narration content",
)
def publish_content(content_id: ContentId, identity: ContentPublishAccess, service: ContentService) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.publish_content(content_id, actor_id=identity.manager_user.id)


@content_router.get(
    "/{content_id}/audio",
    response_model=AdminContentAudioRead,
    summary="Get narration content audio",
)
def get_content_audio(
    content_id: ContentId,
    identity: ContentReadAccess,
    service: AudioService,
) -> AdminContentAudioRead:
    with poi_http_errors():
        return service.get_content_audio(content_id)


@content_router.put(
    "/{content_id}/audio",
    response_model=AdminContentAudioRead,
    summary="Register or replace narration content audio",
)
def save_content_audio(
    content_id: ContentId, payload: AudioMetadataWrite,
    identity: ContentUpdateAccess, service: AudioService,
) -> AdminContentAudioRead:
    """Register/replace metadata of an existing asset; this does not upload bytes."""
    with poi_http_errors():
        return service.save_audio(content_id, payload)


@audio_router.get("", response_model=ContentAudioPage, summary="List narration audios")
def list_audios(
    identity: ContentReadAccess, service: AudioService,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    poi_id: FilterId = None, language_id: FilterId = None,
    poi_content_id: FilterId = None, audio_source_type: AudioSource | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
) -> ContentAudioPage:
    with poi_http_errors():
        return service.list_audios(
            offset=offset, limit=limit, poi_id=poi_id, language_id=language_id,
            poi_content_id=poi_content_id, audio_source_type=audio_source_type, search=search,
        )


@audio_router.get(
    "/{audio_id}",
    response_model=AdminContentAudioRead,
    summary="Get narration audio",
)
def get_audio(
    audio_id: ContentId,
    identity: ContentReadAccess,
    service: AudioService,
) -> AdminContentAudioRead:
    with poi_http_errors():
        return service.get_audio(audio_id)


@router.get(
    "/{poi_id}/narration",
    response_model=PublishedNarration,
    summary="Get published POI narration",
    tags=["POI Content (Public)"],
)
def get_narration(
    poi_id: PoiId, service: ContentService,
    language_code: Annotated[str, Query(pattern=r"^[A-Za-z]{2,3}$")] = "en",
) -> PublishedNarration:
    """Select published narration for an active POI, falling back to English."""
    with poi_http_errors():
        return service.get_narration(poi_id, language_code)
