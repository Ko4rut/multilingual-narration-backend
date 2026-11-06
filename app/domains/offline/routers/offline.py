"""HTTP boundary for public published packages and RBAC-protected admin staging.

No publish route is exposed until a real storage uploader/asset verifier exists.
Preparing a package persists BUILDING metadata and returns a preview only.
"""

import json
from contextlib import contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError

from app.domains.identity.services.authentication import AuthenticatedIdentity
from app.domains.offline.routers.dependencies import (
    get_offline_service, require_offline_create,
    require_offline_read, require_offline_update,
)
from app.domains.offline.schemas.offline_api import (
    OfflinePackagePreparationRead, OfflinePackagePrepareRequest,
    OfflineRebuildPreviewRead, OfflineRebuildPreviewRequest,
)
from app.domains.offline.schemas.offline_package import OfflinePackageRead
from app.domains.offline.schemas.offline_package_item import OfflinePackageItemRead
from app.domains.offline.services.offline import (
    OfflinePackageNotFound, OfflinePackagePreparationError, OfflinePackageService,
)
from app.domains.offline.utils.manifest_diff import InvalidOfflineManifest


router = APIRouter(prefix="/offline", tags=["Offline Packages"])
admin_router = APIRouter(prefix="/admin/offline/packages", tags=["Offline Package Management"])

OfflineService = Annotated[OfflinePackageService, Depends(get_offline_service)]
PackageId = Annotated[str, Path(min_length=1, max_length=50)]
ReadAccess = Annotated[AuthenticatedIdentity, Depends(require_offline_read)]
CreateAccess = Annotated[AuthenticatedIdentity, Depends(require_offline_create)]
UpdateAccess = Annotated[AuthenticatedIdentity, Depends(require_offline_update)]


@contextmanager
def offline_http_errors():
    try:
        yield
    except OfflinePackageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OfflinePackagePreparationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidOfflineManifest as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        # Only translate the known concurrent package-key collision.
        diag = getattr(getattr(exc, "orig", None), "diag", None)
        if getattr(diag, "constraint_name", None) == "uq_offline_package_key":
            raise HTTPException(status_code=409, detail="Offline package already exists") from exc
        raise


@router.get("/packages", response_model=list[OfflinePackageRead],
            summary="List published offline packages")
def list_published_packages(
    service: OfflineService,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    region_id: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    language_id: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    category_id: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
):
    """Mobile discovery. BUILDING/FAILED packages are not returned."""
    return service.list_published_packages(
        region_id=region_id, language_id=language_id,
        category_id=category_id, offset=offset, limit=limit,
    )


@router.get("/packages/{package_id}", response_model=OfflinePackageRead,
            summary="Get a published offline package")
def get_published_package(package_id: PackageId, service: OfflineService):
    with offline_http_errors():
        return service.get_published_package(package_id)


@admin_router.get("", response_model=list[OfflinePackageRead],
                  summary="Admin: list all offline packages")
def list_admin_packages(
    identity: ReadAccess, service: OfflineService,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return service.list_admin_packages(offset=offset, limit=limit)


@admin_router.get("/{package_id}", response_model=OfflinePackageRead,
                  summary="Admin: get offline package details")
def get_admin_package(package_id: PackageId, identity: ReadAccess, service: OfflineService):
    with offline_http_errors():
        return service.get_admin_package(package_id)


@admin_router.get("/{package_id}/items", response_model=list[OfflinePackageItemRead],
                  summary="Admin: list offline package memberships")
def get_admin_package_items(
    package_id: PackageId, identity: ReadAccess, service: OfflineService,
):
    with offline_http_errors():
        return service.get_admin_package_items(package_id)


@admin_router.post("/prepare", response_model=OfflinePackagePreparationRead,
                   status_code=status.HTTP_201_CREATED,
                   summary="Admin: prepare a new BUILDING offline package")
def prepare_offline_package(
    payload: OfflinePackagePrepareRequest, identity: CreateAccess, service: OfflineService,
):
    """Persist initial package/items; preview JSON is NOT published or uploaded."""
    with offline_http_errors():
        package, manifest = service.prepare_initial_package(
            region_id=payload.region_id, language_id=payload.language_id,
            category_id=payload.category_id,
        )
    return OfflinePackagePreparationRead(
        package=OfflinePackageRead.model_validate(package),
        manifest=json.loads(manifest),
    )


@admin_router.post("/{package_id}/rebuild/preview",
                   response_model=OfflineRebuildPreviewRead,
                   summary="Admin: preview changes against a verified published manifest")
def preview_offline_rebuild(
    package_id: PackageId, payload: OfflineRebuildPreviewRequest,
    identity: UpdateAccess, service: OfflineService,
):
    """Read-only diff. Pass exact UTF-8 manifest text so SHA-256 can be checked."""
    with offline_http_errors():
        plan = service.plan_rebuild(
            package_id=package_id,
            published_manifest=payload.published_manifest.encode("utf-8"),
        )
    return OfflineRebuildPreviewRead.from_plan(plan)
