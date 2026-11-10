from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.domains.catalog.repositories.poi_category import PoiCategoryRepository
from app.domains.identity.routers.dependencies import get_authentication_service, get_current_identity
from app.domains.identity.services.authentication import AuthenticatedIdentity, AuthenticationService
from app.domains.poi.repositories.content_audio import ContentAudioRepository
from app.domains.poi.repositories.poi_category_mapping import PoiCategoryMappingRepository
from app.domains.poi.repositories.poi_content import PoiContentRepository
from app.domains.poi.repositories.point_of_interest import PoiRepository
from app.domains.poi.services import PoiAdminService, PoiContentService
from app.route.dependencies import get_session


def get_poi_admin_service(
    session: Annotated[Session, Depends(get_session, use_cache=False)],
) -> PoiAdminService:
    # Auth/RBAC has queried its own Session. A separate business Session lets
    # the service begin a write transaction before its first query.
    return PoiAdminService(
        session=session, repository=PoiRepository(session),
        mappings=PoiCategoryMappingRepository(session), contents=PoiContentRepository(session),
        audios=ContentAudioRepository(session),
        categories=PoiCategoryRepository(session),
    )


def require_poi_management(action_name: str):
    def check_permission(
        identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
        authentication: Annotated[AuthenticationService, Depends(get_authentication_service)],
    ) -> AuthenticatedIdentity:
        if not authentication.has_permission(
            identity.manager_user.id, function_name="POI Management", action_name=action_name,
        ):
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return identity
    return check_permission


require_poi_read = require_poi_management("read")
require_poi_create = require_poi_management("create")
require_poi_update = require_poi_management("update")
require_poi_delete = require_poi_management("delete")


def get_poi_content_service(
    session: Annotated[Session, Depends(get_session, use_cache=False)],
) -> PoiContentService:
    return PoiContentService(
        session=session, pois=PoiRepository(session),
        contents=PoiContentRepository(session), audios=ContentAudioRepository(session),
    )


def require_narration_management(action_name: str):
    def check_permission(
        identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
        authentication: Annotated[AuthenticationService, Depends(get_authentication_service)],
    ) -> AuthenticatedIdentity:
        if not authentication.has_permission(
            identity.manager_user.id, function_name="Narration Content Management", action_name=action_name,
        ):
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return identity
    return check_permission


require_narration_read = require_narration_management("read")
require_narration_create = require_narration_management("create")
require_narration_update = require_narration_management("update")
require_narration_delete = require_narration_management("delete")
require_narration_approve = require_narration_management("approve")
require_narration_publish = require_narration_management("publish")
