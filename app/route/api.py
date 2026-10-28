from fastapi import APIRouter
from app.domains.audit.routers import router as audit_router
from app.domains.catalog.routers import router as catalog_router
from app.domains.identity.routers import router as identity_router
from app.domains.listening.routers import router as listening_router
from app.domains.offline.routers import router as offline_router
from app.domains.poi.routers import router as poi_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(identity_router)
api_router.include_router(catalog_router)
api_router.include_router(poi_router)
api_router.include_router(listening_router)
api_router.include_router(offline_router)
api_router.include_router(audit_router)
