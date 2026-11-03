from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.domains.identity.services.authentication import AuthenticatedIdentity
from app.domains.poi.repositories.point_of_interest import PoiRepository
from app.domains.poi.routers.dependencies import (
    get_poi_admin_service, require_poi_create, require_poi_delete,
    require_poi_read, require_poi_update,
    get_poi_content_service, require_narration_read, require_narration_create,
    require_narration_update, require_narration_delete, require_narration_approve,
    require_narration_publish,
)
from app.domains.poi.routers.http import poi_http_errors
from app.domains.poi.schemas.point_of_interest import (
    AdminPoiPage, AdminPoiRead, PoiCreate, PoiFormOptions, PoiRead,
    PoiStatus, PoiStatusUpdate, PoiUpdate,
)
from app.domains.poi.schemas.content_audio import (
    AdminContentAudioRead, AudioMetadataWrite, AudioSource, ContentAudioPage,
)
from app.domains.poi.schemas.poi_content import (
    AdminPoiContentRead, ContentStatus, PoiContentCreate, PoiContentOptions,
    PoiContentPage, PoiContentUpdate, PoiContentVersionCreate, PublishedNarration,
)
from app.domains.poi.services import PoiAdminService, PoiContentService, PoiService
from app.route.dependencies import get_session


router = APIRouter(prefix="/pois", tags=["POI"])


def get_poi_service(
    session: Annotated[Session, Depends(get_session)],
) -> PoiService:
    return PoiService(PoiRepository(session))


@router.get("", response_model=list[PoiRead])
def list_pois(
    service: Annotated[PoiService, Depends(get_poi_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return service.list_pois(offset=offset, limit=limit)


@router.get("/{poi_id}", response_model=PoiRead)
def get_poi(
    poi_id: Annotated[str, Path(min_length=1, max_length=50)],
    service: Annotated[PoiService, Depends(get_poi_service)],
):
    return service.get_poi(poi_id)


admin_router = APIRouter(prefix="/admin/pois", tags=["POI Management"])
Service = Annotated[PoiAdminService, Depends(get_poi_admin_service)]
PoiId = Annotated[str, Path(min_length=1, max_length=50)]
ReadAccess = Annotated[AuthenticatedIdentity, Depends(require_poi_read)]
CreateAccess = Annotated[AuthenticatedIdentity, Depends(require_poi_create)]
UpdateAccess = Annotated[AuthenticatedIdentity, Depends(require_poi_update)]
DeleteAccess = Annotated[AuthenticatedIdentity, Depends(require_poi_delete)]


@admin_router.get(
    "", response_model=AdminPoiPage,
    summary="List Pois", operation_id="list_pois_api_v1_admin_pois_get",
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


@admin_router.get("/options", response_model=PoiFormOptions)
def get_options(identity: ReadAccess, service: Service) -> PoiFormOptions:
    """Read region/category data for the existing POI form."""
    return service.get_options()


@admin_router.get(
    "/{poi_id}", response_model=AdminPoiRead,
    summary="Get Poi", operation_id="get_poi_api_v1_admin_pois__poi_id__get",
)
def get_admin_poi(poi_id: PoiId, identity: ReadAccess, service: Service) -> AdminPoiRead:
    with poi_http_errors():
        return service.get_poi(poi_id)


@admin_router.post("", response_model=AdminPoiRead, status_code=201)
def create_poi(payload: PoiCreate, identity: CreateAccess, service: Service) -> AdminPoiRead:
    with poi_http_errors():
        return service.create_poi(payload, actor_id=identity.manager_user.id)


@admin_router.patch("/{poi_id}", response_model=AdminPoiRead)
def update_poi(
    poi_id: PoiId, payload: PoiUpdate, identity: UpdateAccess, service: Service,
) -> AdminPoiRead:
    with poi_http_errors():
        return service.update_poi(poi_id, payload, actor_id=identity.manager_user.id)


@admin_router.patch("/{poi_id}/status", response_model=AdminPoiRead)
def update_status(
    poi_id: PoiId, payload: PoiStatusUpdate, identity: UpdateAccess, service: Service,
) -> AdminPoiRead:
    with poi_http_errors():
        return service.update_poi(
            poi_id, PoiUpdate(poi_status=payload.poi_status), actor_id=identity.manager_user.id,
        )


@admin_router.delete("/{poi_id}", status_code=204, response_class=Response)
def delete_poi(poi_id: PoiId, identity: DeleteAccess, service: Service) -> Response:
    with poi_http_errors():
        service.delete_poi(poi_id)
    return Response(status_code=204)


content_router = APIRouter(prefix="/admin/poi-contents", tags=["Narration Content Management"])
audio_router = APIRouter(prefix="/admin/audios", tags=["Narration Audio Metadata"])
ContentService = Annotated[PoiContentService, Depends(get_poi_content_service)]
ContentId = Annotated[str, Path(min_length=1, max_length=50)]
FilterId = Annotated[str | None, Query(min_length=1, max_length=50)]
ContentReadAccess = Annotated[AuthenticatedIdentity, Depends(require_narration_read)]
ContentCreateAccess = Annotated[AuthenticatedIdentity, Depends(require_narration_create)]
ContentUpdateAccess = Annotated[AuthenticatedIdentity, Depends(require_narration_update)]
ContentDeleteAccess = Annotated[AuthenticatedIdentity, Depends(require_narration_delete)]
ContentApproveAccess = Annotated[AuthenticatedIdentity, Depends(require_narration_approve)]
ContentPublishAccess = Annotated[AuthenticatedIdentity, Depends(require_narration_publish)]


@content_router.get("", response_model=PoiContentPage)
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


@content_router.get("/options", response_model=PoiContentOptions)
def get_content_options(identity: ContentReadAccess, service: ContentService) -> PoiContentOptions:
    return service.get_options()


@content_router.get("/{content_id}", response_model=AdminPoiContentRead)
def get_content(content_id: ContentId, identity: ContentReadAccess, service: ContentService) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.get_content(content_id)


@content_router.post("", response_model=AdminPoiContentRead, status_code=201)
def create_content(
    payload: PoiContentCreate, identity: ContentCreateAccess, service: ContentService,
) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.create_content(payload, actor_id=identity.manager_user.id)


@content_router.post("/{content_id}/versions", response_model=AdminPoiContentRead, status_code=201)
def create_content_version(
    content_id: ContentId, payload: PoiContentVersionCreate,
    identity: ContentCreateAccess, service: ContentService,
) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.create_version(content_id, payload, actor_id=identity.manager_user.id)


@content_router.patch("/{content_id}", response_model=AdminPoiContentRead)
def update_content(
    content_id: ContentId, payload: PoiContentUpdate,
    identity: ContentUpdateAccess, service: ContentService,
) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.update_content(content_id, payload)


@content_router.delete("/{content_id}", status_code=204, response_class=Response)
def delete_content(content_id: ContentId, identity: ContentDeleteAccess, service: ContentService) -> Response:
    with poi_http_errors():
        service.delete_content(content_id)
    return Response(status_code=204)


@content_router.post("/{content_id}/submit", response_model=AdminPoiContentRead)
def submit_content(content_id: ContentId, identity: ContentUpdateAccess, service: ContentService) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.submit_content(content_id)


@content_router.post("/{content_id}/approve", response_model=AdminPoiContentRead)
def approve_content(content_id: ContentId, identity: ContentApproveAccess, service: ContentService) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.approve_content(content_id, actor_id=identity.manager_user.id)


@content_router.post("/{content_id}/reject", response_model=AdminPoiContentRead)
def reject_content(content_id: ContentId, identity: ContentApproveAccess, service: ContentService) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.reject_content(content_id)


@content_router.post("/{content_id}/publish", response_model=AdminPoiContentRead)
def publish_content(content_id: ContentId, identity: ContentPublishAccess, service: ContentService) -> AdminPoiContentRead:
    with poi_http_errors():
        return service.publish_content(content_id, actor_id=identity.manager_user.id)


@content_router.get("/{content_id}/audio", response_model=AdminContentAudioRead)
def get_content_audio(content_id: ContentId, identity: ContentReadAccess, service: ContentService) -> AdminContentAudioRead:
    with poi_http_errors():
        return service.get_content_audio(content_id)


@content_router.put("/{content_id}/audio", response_model=AdminContentAudioRead)
def save_content_audio(
    content_id: ContentId, payload: AudioMetadataWrite,
    identity: ContentUpdateAccess, service: ContentService,
) -> AdminContentAudioRead:
    """Register/replace metadata of an existing asset; this does not upload bytes."""
    with poi_http_errors():
        return service.save_audio(content_id, payload)


@content_router.delete("/{content_id}/audio", status_code=204, response_class=Response)
def delete_content_audio(content_id: ContentId, identity: ContentDeleteAccess, service: ContentService) -> Response:
    with poi_http_errors():
        service.delete_audio(content_id)
    return Response(status_code=204)


@audio_router.get("", response_model=ContentAudioPage)
def list_audios(
    identity: ContentReadAccess, service: ContentService,
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


@audio_router.get("/{audio_id}", response_model=AdminContentAudioRead)
def get_audio(audio_id: ContentId, identity: ContentReadAccess, service: ContentService) -> AdminContentAudioRead:
    with poi_http_errors():
        return service.get_audio(audio_id)


@router.get("/{poi_id}/narration", response_model=PublishedNarration)
def get_narration(
    poi_id: PoiId, service: ContentService,
    language_code: Annotated[str, Query(pattern=r"^[A-Za-z]{2,3}$")] = "en",
) -> PublishedNarration:
    """Select published narration for an active POI, falling back to English."""
    with poi_http_errors():
        return service.get_narration(poi_id, language_code)
