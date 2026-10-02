from fastapi import APIRouter
from app.domains.identity.router import router as identity_router
from app.domains.catalog.router import router as catalog_router
from app.domains.poi.router import router as poi_router
from app.domains.narration.router import router as narration_router
from app.domains.listening.router import router as listening_router
from app.domains.offline.router import router as offline_router
from app.domains.audit.router import router as audit_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(identity_router)
api_router.include_router(catalog_router)
api_router.include_router(poi_router)
api_router.include_router(narration_router)
api_router.include_router(listening_router)
api_router.include_router(offline_router)
api_router.include_router(audit_router)
