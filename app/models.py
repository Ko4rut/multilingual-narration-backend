"""Model registry for Alembic and backwards-compatible imports."""
from app.core.database import Base
from app.domains.identity.models import Action, ManagementFunction, Permission, Role, RolePermission, ManagementUser
from app.domains.catalog.models import Region, Language
from app.domains.poi.models import PoiCategory, PointOfInterest, PoiCategoryMapping
from app.domains.narration.models import PoiContent, ContentAudio
from app.domains.listening.models import ListeningHistory
from app.domains.offline.models import OfflinePackage
from app.domains.audit.models import AuditLog

__all__ = ['Base', 'Action', 'ManagementFunction', 'Permission', 'Role', 'RolePermission', 'ManagementUser', 'Region', 'Language', 'PoiCategory', 'PointOfInterest', 'PoiContent', 'ContentAudio', 'ListeningHistory', 'PoiCategoryMapping', 'OfflinePackage', 'AuditLog']
