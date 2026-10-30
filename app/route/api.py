from fastapi import APIRouter
from app.domains.identity.routers.identity import (
    auth_router,
    manager_user_router,
    role_router,
)
from app.domains.audit.routers import router as audit_router
from app.domains.catalog.routers import router as catalog_router
from app.domains.listening.routers import router as listening_router
from app.domains.offline.routers import router as offline_router
from app.domains.poi.routers import router as poi_router

api_router = APIRouter(prefix="/api/v1")

# Domain Identity
api_router.include_router(auth_router)
api_router.include_router(manager_user_router)
api_router.include_router(role_router)

# Domain Audit
api_router.include_router(audit_router)

# Domain Catalog
api_router.include_router(catalog_router)

# Domain POI
api_router.include_router(poi_router)

# Domain Listening
api_router.include_router(listening_router)

# Domain Offline
api_router.include_router(offline_router)

