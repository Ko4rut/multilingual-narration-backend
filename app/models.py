"""ORM registry used by Alembic and compatibility imports."""

from app.core.database import Base
from app.domains.audit.models import AuditLog
from app.domains.catalog.models import Language, PoiCategory, Region
from app.domains.identity.models import (
    Action,
    ManagementFunction,
    ManagerUser,
    Permission,
    Role,
    RolePermission,
    UserSession,
)
from app.domains.listening.models import ListeningHistory
from app.domains.offline.models import OfflinePackage, OfflinePackageItem
from app.domains.poi.models import (
    ContentAudio,
    PoiCategoryMapping,
    PoiContent,
    PointOfInterest,
)

__all__ = [
    "Base",
    "Action",
    "ManagementFunction",
    "Permission",
    "Role",
    "RolePermission",
    "ManagerUser",
    "UserSession",
    "Region",
    "Language",
    "PoiCategory",
    "PointOfInterest",
    "PoiCategoryMapping",
    "PoiContent",
    "ContentAudio",
    "ListeningHistory",
    "OfflinePackage",
    "OfflinePackageItem",
    "AuditLog",
]
