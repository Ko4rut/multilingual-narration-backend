from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.domains.catalog.exceptions import (
    LanguageAlreadyExists,
    LanguageNotFound,
    PoiCategoryAlreadyExists,
    PoiCategoryInUse,
    PoiCategoryNotFound,
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
    PoiCategoryCreate,
    PoiCategoryRead,
    PoiCategoryUpdate,
    RegionRead,
)
from app.domains.catalog.services import CatalogService
from app.domains.identity.routers.dependencies import require_permission
from app.route.dependencies import get_session

router = APIRouter(prefix="/catalog")
admin_router = APIRouter(prefix="/admin/catalog")

require_language_read = require_permission("Language Management", "read")
require_language_create = require_permission("Language Management", "create")
require_language_update = require_permission("Language Management", "update")

# Categories classify POIs, so reuse the existing POI Management RBAC actions.
require_category_read = require_permission("POI Management", "read")
require_category_create = require_permission("POI Management", "create")
require_category_update = require_permission("POI Management", "update")
require_category_delete = require_permission("POI Management", "delete")

CategoryId = Annotated[str, Path(min_length=1, max_length=50)]


def get_catalog_service(
    session: Annotated[Session, Depends(get_session, use_cache=False)],
) -> CatalogService:
    return CatalogService(
        session=session,
        language_repository=LanguageRepository(session),
        region_repository=RegionRepository(session),
        category_repository=PoiCategoryRepository(session),
    )


@router.get(
    "/regions",
    response_model=list[RegionRead],
    summary="List regions",
    tags=["Region (Public)"],
)
def list_regions(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
):
    """Return every region ordered by identifier."""

    return service.list_regions()


@router.get(
    "/categories",
    response_model=list[PoiCategoryRead],
    summary="List POI categories",
    tags=["POI Category (Public)"],
)
def list_categories(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
):
    """Return every POI category ordered by identifier."""

    return service.list_categories()


@router.get(
    "/languages",
    response_model=list[LanguageRead],
    summary="List supported languages",
    tags=["Language (Public)"],
)
def list_supported_languages(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
):
    return service.list_supported_languages()


@admin_router.get(
    "/languages",
    response_model=list[LanguageRead],
    summary="List languages",
    tags=["Language"],
    dependencies=[Depends(require_language_read)],
)
def list_languages(service: Annotated[CatalogService, Depends(get_catalog_service)]):
    return service.list_languages()


@admin_router.post(
    "/languages",
    response_model=LanguageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a language",
    tags=["Language"],
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
    summary="Update a language",
    tags=["Language"],
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


@admin_router.get(
    "/categories",
    response_model=list[PoiCategoryRead],
    summary="Admin: list POI categories",
    tags=["POI Category"],
    dependencies=[Depends(require_category_read)],
)
def list_admin_categories(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
):
    return service.list_categories()


@admin_router.post(
    "/categories",
    response_model=PoiCategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: create POI category",
    tags=["POI Category"],
    dependencies=[Depends(require_category_create)],
)
def create_category(
    payload: PoiCategoryCreate,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
):
    try:
        return service.create_category(**payload.model_dump())
    except PoiCategoryAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.patch(
    "/categories/{category_id}",
    response_model=PoiCategoryRead,
    summary="Admin: rename POI category",
    tags=["POI Category"],
    dependencies=[Depends(require_category_update)],
)
def update_category(
    category_id: CategoryId,
    payload: PoiCategoryUpdate,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
):
    try:
        return service.update_category(
            category_id, **payload.model_dump(),
        )
    except PoiCategoryNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PoiCategoryAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Admin: delete unreferenced POI category",
    tags=["POI Category"],
    dependencies=[Depends(require_category_delete)],
)
def delete_category(
    category_id: CategoryId,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> None:
    try:
        service.delete_category(category_id)
    except PoiCategoryNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PoiCategoryInUse as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
