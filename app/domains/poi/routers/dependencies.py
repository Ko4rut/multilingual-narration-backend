from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.domains.catalog.repositories.poi_category import PoiCategoryRepository
from app.domains.catalog.repositories.region import RegionRepository
from app.domains.identity.routers.dependencies import get_authentication_service, get_current_identity
from app.domains.identity.services.authentication import AuthenticatedIdentity, AuthenticationService
from app.domains.poi.repositories.content_audio import ContentAudioRepository
from app.domains.poi.repositories.poi_category_mapping import PoiCategoryMappingRepository
from app.domains.poi.repositories.poi_content import PoiContentRepository
from app.domains.poi.repositories.point_of_interest import PoiRepository
from app.domains.poi.providers.image_checksum import RemoteImageChecksumProvider
from app.domains.poi.providers.audio_asset import RemoteAudioAssetProvider
from app.domains.poi.services import (
    ContentAudioService,
    PointOfInterestService,
    PoiContentService,
)
from app.domains.poi.providers.tts import FileSystemTtsStorage, GttsSynthesizer
from app.core.config import get_settings
from app.route.dependencies import get_session


def get_point_of_interest_service(
    session: Annotated[Session, Depends(get_session, use_cache=False)],
) -> PointOfInterestService:
    # Auth/RBAC has queried its own Session. A separate business Session lets
    # the service begin a write transaction before its first query.
    return PointOfInterestService(
        session=session, repository=PoiRepository(session),
        mappings=PoiCategoryMappingRepository(session), contents=PoiContentRepository(session),
        audios=ContentAudioRepository(session),
        category_repository=PoiCategoryRepository(session),
        region_repository=RegionRepository(session),
        image_checksums=RemoteImageChecksumProvider(),
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


def get_poi_content_service(
    session: Annotated[Session, Depends(get_session, use_cache=False)],
) -> PoiContentService:
    settings = get_settings()
    return PoiContentService(
        session=session, pois=PoiRepository(session),
        contents=PoiContentRepository(session), audios=ContentAudioRepository(session),
        tts=GttsSynthesizer(),
        tts_storage=FileSystemTtsStorage(
            settings.tts_audio_dir, settings.tts_audio_public_base_url,
        ),
    )


def get_content_audio_service(
    session: Annotated[Session, Depends(get_session, use_cache=False)],
) -> ContentAudioService:
    return ContentAudioService(
        session=session,
        pois=PoiRepository(session),
        contents=PoiContentRepository(session),
        audios=ContentAudioRepository(session),
        audio_assets=RemoteAudioAssetProvider(),
    )


def get_tts_storage() -> FileSystemTtsStorage:
    settings = get_settings()
    return FileSystemTtsStorage(
        settings.tts_audio_dir, settings.tts_audio_public_base_url,
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
require_narration_approve = require_narration_management("approve")
require_narration_publish = require_narration_management("publish")
