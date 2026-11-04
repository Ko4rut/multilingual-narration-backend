from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.domains.catalog.exceptions import (
    LanguageAlreadyExists,
    LanguageInUse,
    LanguageNotFound,
)
from app.domains.catalog.repositories import (
    LanguageRepository,
    PoiCategoryRepository,
    RegionRepository,
)
from app.domains.catalog.schemas import (
    LanguageCreate,
    LanguageRead,
    LanguageUpdate,
    PoiCategoryRead,
    RegionRead,
)
from app.domains.catalog.services import CatalogService
from app.domains.identity.routers.dependencies import require_permission
from app.route.dependencies import get_session

router = APIRouter(prefix="/catalog", tags=["catalog"])
admin_router = APIRouter(prefix="/admin/catalog", tags=["admin-catalog"])

require_language_read = require_permission("Language Management", "read")
require_language_create = require_permission("Language Management", "create")
require_language_update = require_permission("Language Management", "update")
require_language_delete = require_permission("Language Management", "delete")


def get_catalog_service(
    session: Annotated[Session, Depends(get_session, use_cache=False)],
) -> CatalogService:
    return CatalogService(
        session=session,
        language_repository=LanguageRepository(session),
        region_repository=RegionRepository(session),
        poi_category_repository=PoiCategoryRepository(session),
    )


@router.get("/regions", response_model=list[RegionRead])
def list_regions(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
):
    """Return every region ordered by identifier."""

    return service.list_regions()


@router.get("/categories", response_model=list[PoiCategoryRead])
def list_categories(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
):
    """Return every POI category ordered by identifier."""

    return service.list_categories()


@router.get("/languages", response_model=list[LanguageRead])
def list_supported_languages(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
):
    return service.list_supported_languages()


@admin_router.get(
    "/languages",
    response_model=list[LanguageRead],
    dependencies=[Depends(require_language_read)],
)
def list_languages(service: Annotated[CatalogService, Depends(get_catalog_service)]):
    return service.list_languages()


@admin_router.post(
    "/languages",
    response_model=LanguageRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_language_create)],
)
def create_language(
    payload: LanguageCreate,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
):
    try:
        return service.create_language(**payload.model_dump())
    except LanguageAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.patch(
    "/languages/{language_id}",
    response_model=LanguageRead,
    dependencies=[Depends(require_language_update)],
)
def update_language(
    language_id: str,
    payload: LanguageUpdate,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
):
    try:
        return service.update_language(language_id, **payload.model_dump(exclude_unset=True))
    except LanguageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LanguageAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.delete(
    "/languages/{language_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_language_delete)],
)
def delete_language(
    language_id: str,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> Response:
    try:
        service.delete_language(language_id)
    except LanguageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LanguageInUse as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
