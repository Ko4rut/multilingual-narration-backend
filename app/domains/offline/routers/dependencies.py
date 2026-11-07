"""Offline Group 3 dependency wiring and RBAC permissions."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domains.identity.routers.dependencies import require_permission
from app.domains.offline.repositories.offline_package import OfflinePackageRepository
from app.domains.offline.repositories.offline_package_item import OfflinePackageItemRepository
from app.domains.offline.services.offline import OfflinePackageService
from app.domains.offline.storage.manifest import FileSystemManifestStorage
from app.route.dependencies import get_session


def get_offline_service(
    session: Annotated[Session, Depends(get_session, use_cache=False)],
) -> OfflinePackageService:
    # Separate from the authentication/RBAC session: the offline service owns
    # the write transaction from its first query.
    return OfflinePackageService(
        session=session,
        packages=OfflinePackageRepository(session),
        items=OfflinePackageItemRepository(session),
        manifest_storage=FileSystemManifestStorage(get_settings().offline_manifest_dir),
    )


require_offline_read = require_permission("Offline Package Management", "read")
require_offline_create = require_permission("Offline Package Management", "create")
require_offline_update = require_permission("Offline Package Management", "update")
